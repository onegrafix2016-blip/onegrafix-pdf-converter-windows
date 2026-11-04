import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QFileDialog,
    QVBoxLayout, QHBoxLayout, QGridLayout, QProgressBar, QCheckBox,
    QMessageBox, QListWidget, QGroupBox, QLineEdit, QInputDialog
)
from .converters import convert_file

APP_NAME = "OneGrafix PDF Converter"


def parse_page_range(value, total):
    """Parse 1-based page ranges such as 1-3,5. Return zero-based indices."""
    value = value.strip()
    if not value:
        return None
    result = []
    for part in value.split(","):
        part = part.strip()
        if "-" in part:
            pieces = part.split("-", 1)
            start, end = int(pieces[0]), int(pieces[1])
        else:
            start = end = int(part)
        if start < 1 or end < start or end > total:
            raise ValueError(f"Invalid page range '{part}'. This PDF has {total} pages.")
        result.extend(range(start - 1, end))
    return sorted(set(result))


class BatchWorker(QObject):
    progress = Signal(int)
    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, kind, sources, output_dir, use_ocr, page_range, passwords=None):
        super().__init__()
        self.kind = kind
        self.sources = sources
        self.output_dir = Path(output_dir)
        self.use_ocr = use_ocr
        self.page_range = page_range
        self.passwords = passwords or {}

    def run(self):
        outputs = []
        try:
            ext = {"pdf_word": ".docx", "pdf_excel": ".xlsx",
                   "word_pdf": ".pdf", "excel_pdf": ".pdf"}[self.kind]
            for file_index, source in enumerate(self.sources):
                source = Path(source)
                destination = self.output_dir / (source.stem + "_converted" + ext)
                suffix = 1
                while destination.exists():
                    destination = self.output_dir / (source.stem + f"_converted_{suffix}" + ext)
                    suffix += 1
                pages = None
                if self.kind in ("pdf_word", "pdf_excel") and self.page_range.strip():
                    import fitz
                    with fitz.open(source) as pdf:
                        password = self.passwords.get(str(source))
                        if pdf.needs_pass and not (password and pdf.authenticate(password)):
                            raise RuntimeError(f'{source.name} is password-protected. Enter the correct password and retry.')
                        pages = parse_page_range(self.page_range, len(pdf))
                def local_progress(value, i=file_index):
                    overall = int((i * 100 + value) / len(self.sources))
                    self.progress.emit(overall)
                password = self.passwords.get(str(source))
                convert_file(self.kind, str(source), str(destination), self.use_ocr,
                             pages=pages, progress=local_progress, password=password)
                outputs.append(str(destination))
            self.finished.emit(outputs)
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(920, 700)
        self.setMinimumSize(780, 620)
        self.kind = None
        self.sources = []
        self.thread = None
        self.worker = None
        self.output_dir = None

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header = QHBoxLayout()
        brand = QVBoxLayout()
        title = QLabel(APP_NAME)
        title.setObjectName("title")
        subtitle = QLabel("Convert. Edit. Create. Simplify.")
        subtitle.setObjectName("subtitle")
        brand.addWidget(title)
        brand.addWidget(subtitle)
        header.addLayout(brand)
        header.addStretch()
        status = QLabel("OFFLINE DOCUMENT CONVERSION")
        status.setObjectName("status")
        header.addWidget(status)
        layout.addLayout(header)

        intro = QLabel("Choose a conversion")
        intro.setObjectName("section")
        layout.addWidget(intro)

        grid = QGridLayout()
        grid.setSpacing(12)
        actions = [
            ("PDF  →  Word", "pdf_word", "Editable DOCX document"),
            ("PDF  →  Excel", "pdf_excel", "Extract tables and OCR text"),
            ("Word  →  PDF", "word_pdf", "DOCX / DOC to PDF"),
            ("Excel  →  PDF", "excel_pdf", "XLSX / XLS to PDF"),
        ]
        for i, (label, kind, desc) in enumerate(actions):
            btn = QPushButton(label + "\n" + desc)
            btn.setObjectName("conversion")
            btn.setMinimumHeight(82)
            btn.clicked.connect(lambda checked=False, k=kind: self.choose_files(k))
            grid.addWidget(btn, i // 2, i % 2)
        layout.addLayout(grid)

        box = QGroupBox("Conversion settings")
        box_layout = QVBoxLayout(box)
        self.file_label = QLabel("No files selected. Choose a conversion above.")
        self.file_label.setWordWrap(True)
        box_layout.addWidget(self.file_label)

        settings = QHBoxLayout()
        self.ocr = QCheckBox("Enable offline OCR for scanned PDFs (English)")
        self.ocr.setChecked(True)
        settings.addWidget(self.ocr)
        settings.addStretch()
        settings.addWidget(QLabel("PDF pages:"))
        self.page_range = QLineEdit()
        self.page_range.setPlaceholderText("All pages (e.g. 1-3,5)")
        self.page_range.setMaximumWidth(180)
        settings.addWidget(self.page_range)
        box_layout.addLayout(settings)
        note = QLabel("Page selection applies to PDF conversions. Leave blank to process all pages.")
        note.setObjectName("hint")
        box_layout.addWidget(note)
        layout.addWidget(box)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        controls = QHBoxLayout()
        self.convert_btn = QPushButton("Convert selected files")
        self.convert_btn.setObjectName("primary")
        self.convert_btn.setEnabled(False)
        self.convert_btn.clicked.connect(self.start_conversion)
        self.folder_btn = QPushButton("Choose output folder")
        self.folder_btn.clicked.connect(self.choose_output_folder)
        self.output_label = QLabel("Output: Same folder as source files")
        self.output_label.setObjectName("hint")
        controls.addWidget(self.convert_btn)
        controls.addWidget(self.folder_btn)
        controls.addWidget(self.output_label, 1)
        layout.addLayout(controls)

        history_title = QLabel("Recent conversions")
        history_title.setObjectName("section")
        layout.addWidget(history_title)
        self.history = QListWidget()
        self.history.setMaximumHeight(115)
        layout.addWidget(self.history)

        self.open_btn = QPushButton("Open last output folder")
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self.open_output)
        layout.addWidget(self.open_btn)

        footer = QLabel("Developed by OneHost Digital  •  Files are processed locally on this computer")
        footer.setObjectName("footer")
        layout.addWidget(footer)

        self.setStyleSheet("""
            QMainWindow, QWidget { background: #f5f8fc; color: #172b45; font-family: 'Segoe UI'; font-size: 10pt; }
            QLabel#title { color: #102b50; font-size: 22pt; font-weight: 700; }
            QLabel#subtitle { color: #4c78a8; font-size: 10pt; }
            QLabel#status { color: #ffffff; background: #173c68; padding: 8px 12px; border-radius: 8px; font-size: 8pt; font-weight: 700; }
            QLabel#section { color: #102b50; font-size: 14pt; font-weight: 650; margin-top: 5px; }
            QLabel#hint, QLabel#footer { color: #72869c; font-size: 8pt; }
            QPushButton#conversion { background: #ffffff; border: 1px solid #d5e2f0; border-radius: 12px; color: #173c68; text-align: left; padding: 16px; font-size: 11pt; font-weight: 700; }
            QPushButton#conversion:hover { border: 2px solid #56a5e8; background: #edf6ff; }
            QPushButton#primary { background: #176bb2; color: white; border: 0; border-radius: 8px; padding: 12px 22px; font-weight: 700; }
            QPushButton#primary:disabled { background: #a9bfd4; }
            QPushButton { padding: 9px 14px; border-radius: 7px; border: 1px solid #c9d7e5; background: white; }
            QGroupBox { border: 1px solid #d5e2f0; border-radius: 10px; margin-top: 10px; padding: 12px; background: white; font-weight: 650; }
            QLineEdit { background: white; border: 1px solid #c9d7e5; border-radius: 6px; padding: 8px; }
            QProgressBar { border: 0; border-radius: 6px; background: #e0eaf4; height: 14px; text-align: center; }
            QProgressBar::chunk { background: #2186cf; border-radius: 6px; }
            QListWidget { background: white; border: 1px solid #d5e2f0; border-radius: 8px; }
        """)

    def choose_files(self, kind):
        filters = {
            "pdf_word": "PDF files (*.pdf)",
            "pdf_excel": "PDF files (*.pdf)",
            "word_pdf": "Word documents (*.docx *.doc)",
            "excel_pdf": "Excel workbooks (*.xlsx *.xls)"
        }
        paths, _ = QFileDialog.getOpenFileNames(self, "Select one or more documents", "", filters[kind])
        if not paths:
            return
        self.kind = kind
        self.sources = [Path(p) for p in paths]
        total_kb = sum(p.stat().st_size for p in self.sources) / 1024
        self.file_label.setText(f"{len(self.sources)} file(s) selected  •  {total_kb:,.1f} KB total\n" +
                                "\n".join(p.name for p in self.sources[:5]) +
                                ("\n…" if len(self.sources) > 5 else ""))
        self.convert_btn.setEnabled(True)
        self.progress.setValue(0)

    def choose_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if folder:
            self.output_dir = Path(folder)
            self.output_label.setText(f"Output: {folder}")

    def start_conversion(self):
        if not self.sources:
            return
        output_dir = self.output_dir or self.sources[0].parent
        passwords = {}
        if self.kind in ("pdf_word", "pdf_excel"):
            try:
                import fitz
                for selected_file in self.sources:
                    with fitz.open(selected_file) as selected_pdf:
                        if selected_pdf.needs_pass:
                            password, accepted = QInputDialog.getText(
                                self, "PDF password",
                                f"Enter the password for {selected_file.name}:",
                                QLineEdit.EchoMode.Password
                            )
                            if not accepted or not password:
                                return
                            if not selected_pdf.authenticate(password):
                                QMessageBox.warning(
                                    self, "Incorrect password",
                                    f"The password for {selected_file.name} is incorrect."
                                )
                                return
                            passwords[str(selected_file)] = password
            except Exception as exc:
                QMessageBox.critical(self, "Cannot open PDF", str(exc))
                return

        self.convert_btn.setEnabled(False)
        self.folder_btn.setEnabled(False)
        self.progress.setValue(0)
        self.thread = QThread()
        self.worker = BatchWorker(self.kind, [str(p) for p in self.sources],
                                  str(output_dir), self.ocr.isChecked(), self.page_range.text(), passwords)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self.on_success)
        self.worker.failed.connect(self.on_failure)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def on_success(self, paths):
        self.convert_btn.setEnabled(True)
        self.folder_btn.setEnabled(True)
        self.output_dir = Path(paths[-1]).parent if paths else self.output_dir
        for path in paths:
            self.history.insertItem(0, Path(path).name)
        self.open_btn.setEnabled(bool(paths))
        QMessageBox.information(self, "Batch conversion complete",
                                f"Successfully converted {len(paths)} file(s).")

    def on_failure(self, message):
        self.convert_btn.setEnabled(True)
        self.folder_btn.setEnabled(True)
        QMessageBox.critical(self, "Conversion failed", message)

    def open_output(self):
        if self.output_dir and self.output_dir.exists():
            import os
            os.startfile(str(self.output_dir))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
