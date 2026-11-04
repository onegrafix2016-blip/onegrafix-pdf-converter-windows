import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

import fitz
from docx import Document
from openpyxl import load_workbook
from PIL import Image, ImageDraw, ImageFont
import shutil

from onegrafix_converter.converters import (
    pdf_to_word, pdf_to_excel, office_to_pdf, _find_libreoffice
)


class ConversionSmokeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.pdf_path = self.root / "sample.pdf"
        pdf = fitz.open()
        page = pdf.new_page()
        page.insert_text((72, 72), "OneGrafix conversion test\nInvoice: OG-100\nAmount: 125.50")
        pdf.save(self.pdf_path)
        pdf.close()

    def tearDown(self):
        self.temp.cleanup()

    def test_pdf_to_word(self):
        target = self.root / "sample.docx"
        pdf_to_word(self.pdf_path, target, use_ocr=False)
        text = "\n".join(p.text for p in Document(target).paragraphs)
        self.assertIn("Invoice: OG-100", text)
        self.assertIn("125.50", text)

    def test_pdf_to_excel_creates_workbook(self):
        target = self.root / "sample.xlsx"
        pdf_to_excel(self.pdf_path, target, use_ocr=False)
        workbook = load_workbook(target)
        self.assertGreaterEqual(len(workbook.sheetnames), 1)
        self.assertIn("OneGrafix", " ".join(
            str(c.value or "") for row in workbook.active.iter_rows() for c in row
        ))

    def test_password_protected_pdf(self):
        protected = self.root / "locked.pdf"
        pdf = fitz.open()
        page = pdf.new_page()
        page.insert_text((72, 72), "Protected OneGrafix test")
        pdf.save(protected, encryption=fitz.PDF_ENCRYPT_AES_256,
                 owner_pw="owner", user_pw="secret")
        pdf.close()

        with self.assertRaises(Exception):
            pdf_to_word(protected, self.root / "no_password.docx", use_ocr=False)

        output = self.root / "with_password.docx"
        pdf_to_word(protected, output, use_ocr=False, password="secret")
        text = "\n".join(p.text for p in Document(output).paragraphs)
        self.assertIn("Protected OneGrafix test", text)

    def test_pdf_images_are_embedded_in_word(self):
        image_path = self.root / "logo.png"
        image = Image.new("RGB", (180, 90), "white")
        ImageDraw.Draw(image).rectangle((15, 15, 165, 75), fill="blue")
        image.save(image_path)

        image_pdf = self.root / "with_image.pdf"
        pdf = fitz.open()
        page = pdf.new_page()
        page.insert_image(fitz.Rect(50, 50, 230, 140), filename=str(image_path))
        pdf.save(image_pdf)
        pdf.close()

        output = self.root / "with_image.docx"
        pdf_to_word(image_pdf, output, use_ocr=False)
        with ZipFile(output) as archive:
            media = [name for name in archive.namelist() if name.startswith("word/media/")]
        self.assertTrue(media, "Expected embedded image in DOCX output")


    def test_password_protected_pdf_to_excel(self):
        protected = self.root / "locked_excel.pdf"
        pdf = fitz.open()
        page = pdf.new_page()
        page.insert_text((72, 72), "Protected Excel export test")
        pdf.save(protected, encryption=fitz.PDF_ENCRYPT_AES_256,
                 owner_pw="owner", user_pw="secret")
        pdf.close()

        output = self.root / "protected.xlsx"
        pdf_to_excel(protected, output, use_ocr=False, password="secret")
        workbook = load_workbook(output)
        text = " ".join(
            str(cell.value or "") for row in workbook.active.iter_rows() for cell in row
        )
        self.assertIn("Protected Excel export test", text)

    def test_desktop_ui_module_imports(self):
        # The native Windows build installs PySide6; skip only in minimal test environments.
        import importlib.util
        if importlib.util.find_spec("PySide6") is None:
            self.skipTest("PySide6 is not installed in this environment")
        from onegrafix_converter.main import MainWindow
        self.assertTrue(callable(MainWindow))

    def test_word_to_pdf_when_libreoffice_available(self):
        if not _find_libreoffice():
            self.skipTest("LibreOffice not installed")
        docx = self.root / "source.docx"
        Document().save(docx)
        target = self.root / "source.pdf"
        office_to_pdf(docx, target)
        self.assertTrue(target.exists())
        self.assertGreater(target.stat().st_size, 0)

    def test_scanned_pdf_ocr_when_tesseract_available(self):
        if not shutil.which("tesseract"):
            self.skipTest("Tesseract not installed in test environment")
        image = Image.new("RGB", (1500, 350), "white")
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 64)
        except OSError:
            font = ImageFont.load_default()
        draw.text((40, 80), "ONEGRAFIX OCR 245.00", fill="black", font=font)
        png = self.root / "scan.png"
        image.save(png)

        scanned_pdf = self.root / "scan.pdf"
        pdf = fitz.open()
        page = pdf.new_page(width=750, height=175)
        page.insert_image(page.rect, filename=str(png))
        pdf.save(scanned_pdf)
        pdf.close()

        word_output = self.root / "scan.docx"
        pdf_to_word(scanned_pdf, word_output, use_ocr=True)
        word_text = "\n".join(p.text for p in Document(word_output).paragraphs)
        self.assertIn("ONEGRAFIX", word_text.upper())

        excel_output = self.root / "scan.xlsx"
        pdf_to_excel(scanned_pdf, excel_output, use_ocr=True)
        workbook = load_workbook(excel_output)
        excel_text = " ".join(
            str(cell.value or "") for row in workbook.active.iter_rows() for cell in row
        )
        self.assertIn("ONEGRAFIX", excel_text.upper())


if __name__ == "__main__":
    unittest.main()
