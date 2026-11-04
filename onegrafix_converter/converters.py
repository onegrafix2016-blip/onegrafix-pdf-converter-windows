from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from io import BytesIO

import fitz
import pdfplumber
from docx import Document
from docx.shared import Inches
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from PIL import Image
import pytesseract
from pytesseract import Output


def _configure_tesseract():
    """Locate the bundled offline OCR engine or use a system installation."""
    candidates = []
    if getattr(sys, "frozen", False):
        app_dir = Path(sys.executable).resolve().parent
        candidates.extend([
            app_dir / "runtime" / "tesseract" / "tesseract.exe",
            app_dir / "_internal" / "runtime" / "tesseract" / "tesseract.exe",
        ])
    else:
        candidates.append(Path(__file__).resolve().parents[1] / "runtime" / "tesseract" / "tesseract.exe")

    for exe in candidates:
        if exe.is_file():
            tessdata = exe.parent / "tessdata"
            if not (tessdata / "eng.traineddata").is_file():
                raise RuntimeError(
                    f"Offline OCR language data is missing: {tessdata / 'eng.traineddata'}"
                )
            pytesseract.pytesseract.tesseract_cmd = str(exe)
            os.environ["TESSDATA_PREFIX"] = str(tessdata)
            return True

    system_tesseract = shutil.which("tesseract")
    if system_tesseract:
        pytesseract.pytesseract.tesseract_cmd = system_tesseract
        return True
    return False


def _validate_pages(selected, total_pages):
    if selected is None:
        return list(range(total_pages))
    pages = sorted(set(selected))
    if not pages:
        raise ValueError("Select at least one PDF page.")
    if any(not isinstance(p, int) or p < 0 or p >= total_pages for p in pages):
        raise ValueError(f"Page selection is invalid. This PDF contains {total_pages} pages.")
    return pages


def _ocr_image_words(image):
    """Return OCR words grouped into visual lines with approximate columns."""
    data = pytesseract.image_to_data(image, lang="eng", output_type=Output.DICT)
    lines = defaultdict(list)
    for i, word in enumerate(data["text"]):
        word = word.strip()
        try:
            confidence = float(data["conf"][i])
        except (TypeError, ValueError):
            confidence = -1
        if not word or confidence < 25:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines[key].append({
            "text": word, "x": int(data["left"][i]),
            "width": int(data["width"][i])
        })

    rows = []
    for key in sorted(lines):
        words = sorted(lines[key], key=lambda item: item["x"])
        if not words:
            continue
        char_widths = [
            max(4, item["width"] / max(1, len(item["text"])))
            for item in words
        ]
        gap_threshold = max(18, (sum(char_widths) / len(char_widths)) * 2.5)
        cells, current, previous_right = [], [], None
        for item in words:
            if previous_right is not None and item["x"] - previous_right > gap_threshold:
                cells.append(" ".join(current))
                current = []
            current.append(item["text"])
            previous_right = item["x"] + item["width"]
        if current:
            cells.append(" ".join(current))
        rows.append(cells)
    return rows


def _add_page_images_to_docx(doc, page):
    """Embed raster images found on a PDF page; placement is approximate."""
    seen = set()
    for image_info in page.get_images(full=True):
        xref = image_info[0]
        if xref in seen:
            continue
        seen.add(xref)
        try:
            extracted = page.parent.extract_image(xref)
            image_bytes = extracted.get("image")
            if image_bytes:
                doc.add_picture(BytesIO(image_bytes), width=Inches(5.8))
        except Exception:
            # Some PDF image masks or malformed image objects cannot be extracted.
            continue


def pdf_to_word(source, destination, use_ocr=True, pages=None, progress=None, password=None):
    source, destination = Path(source), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    pdf = fitz.open(source)
    try:
        if pdf.needs_pass and not (password and pdf.authenticate(password)):
            raise RuntimeError("This PDF is password-protected. Enter the correct password and retry.")
        selected = _validate_pages(pages, len(pdf))
        if use_ocr and not _configure_tesseract():
            raise RuntimeError("OCR is enabled but Tesseract was not found. Install or bundle offline Tesseract.")

        doc = Document()
        for idx, page_no in enumerate(selected):
            page = pdf[page_no]
            text = page.get_text("text").strip()
            if text:
                for para in text.split("\n\n"):
                    para = para.strip()
                    if para:
                        doc.add_paragraph(para)
            elif use_ocr:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                try:
                    pix.save(tmp_path)
                    with Image.open(tmp_path) as image:
                        recognized = pytesseract.image_to_string(image, lang="eng")
                    for para in recognized.split("\n\n"):
                        if para.strip():
                            doc.add_paragraph(para.strip())
                finally:
                    tmp_path.unlink(missing_ok=True)

            _add_page_images_to_docx(doc, page)
            if idx < len(selected) - 1:
                doc.add_page_break()
            if progress:
                progress(int((idx + 1) * 100 / max(1, len(selected))))
        doc.save(destination)
    finally:
        pdf.close()


def _style_worksheet(ws):
    ws.freeze_panes = "A2"
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="173C68")
    for col in ws.columns:
        letter = col[0].column_letter
        max_len = max((len(str(c.value or "")) for c in col), default=10)
        ws.column_dimensions[letter].width = min(max(max_len + 2, 12), 48)
    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)


def pdf_to_excel(source, destination, pages=None, use_ocr=True, progress=None, password=None):
    source, destination = Path(source), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    wb.remove(wb.active)

    with pdfplumber.open(source, password=password or "") as pdf:
        selected = _validate_pages(pages, len(pdf.pages))
        ocr_ready = _configure_tesseract() if use_ocr else False

        for count, page_no in enumerate(selected):
            page = pdf.pages[page_no]
            tables = page.extract_tables()
            if tables:
                for table_no, table in enumerate(tables, start=1):
                    ws = wb.create_sheet(title=f"P{page_no+1}_T{table_no}"[:31])
                    for row in table:
                        ws.append([cell.strip() if isinstance(cell, str) else cell for cell in row])
                    _style_worksheet(ws)
            else:
                # Prefer the PDF's native text layer; OCR is only a fallback for image-only pages.
                native_text = (page.extract_text() or "").strip()
                if native_text:
                    ws = wb.create_sheet(title=f"Page_{page_no+1}"[:31])
                    for line in native_text.splitlines():
                        ws.append([line])
                    _style_worksheet(ws)
                elif use_ocr and ocr_ready:
                    rendered = page.to_image(resolution=220).original
                    rows = _ocr_image_words(rendered)
                    if rows:
                        ws = wb.create_sheet(title=f"Page_{page_no+1}_OCR"[:31])
                        for row in rows:
                            ws.append(row)
                        _style_worksheet(ws)
            if progress:
                progress(int((count + 1) * 100 / max(1, len(selected))))

    if not wb.sheetnames:
        ws = wb.create_sheet("Extracted Text")
        ws.append(["No tables or text could be extracted from the selected PDF pages."])
    wb.save(destination)


def _find_libreoffice():
    candidates = [
        shutil.which("soffice"),
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    return next((p for p in candidates if p and Path(p).is_file()), None)


def office_to_pdf(source, destination, progress=None):
    source, destination = Path(source), Path(destination)
    if not source.is_file():
        raise FileNotFoundError(f"Source document not found: {source}")
    soffice = _find_libreoffice()
    if not soffice:
        raise RuntimeError(
            "LibreOffice was not found. Install LibreOffice to enable Word/Excel to PDF conversion."
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="onegrafix_lo_") as temp_root:
        outdir = Path(temp_root) / "out"
        profile = Path(temp_root) / "profile"
        outdir.mkdir()
        profile.mkdir()
        profile_uri = profile.resolve().as_uri()
        result = subprocess.run(
            [
                soffice, "--headless", f"-env:UserInstallation={profile_uri}",
                "--convert-to", "pdf", "--outdir", str(outdir), str(source)
            ],
            capture_output=True, text=True, timeout=240
        )
        generated = outdir / (source.stem + ".pdf")
        if result.returncode != 0 or not generated.exists():
            detail = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(detail or "LibreOffice conversion failed.")
        shutil.copy2(generated, destination)
    if progress:
        progress(100)


def convert_file(kind, source, destination, use_ocr=True, pages=None, progress=None, password=None):
    kind = kind.lower()
    if kind == "pdf_word":
        return pdf_to_word(source, destination, use_ocr, pages, progress, password)
    if kind == "pdf_excel":
        return pdf_to_excel(source, destination, pages, use_ocr, progress, password)
    if kind in ("word_pdf", "excel_pdf"):
        return office_to_pdf(source, destination, progress)
    raise ValueError(f"Unsupported conversion type: {kind}")
