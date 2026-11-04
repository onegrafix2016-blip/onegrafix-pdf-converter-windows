# OneGrafix PDF Converter — Build and Test Report

Date: 2026-11-03

## Current environment
The available development environment is Linux x86_64. It does not have PySide6,
PyInstaller, or Inno Setup installed. A native Windows `.exe` installer therefore
cannot be compiled or installation-tested in this session.

## Latest automated test run
Command: `python -m unittest discover -s tests -v`

Result: **8 tests run — 7 passed, 1 skipped, 0 failed.**

Passed:
- PDF text to editable DOCX
- PDF text to XLSX workbook
- Password-protected PDF to DOCX with correct password
- Password-protected PDF to XLSX with correct password
- Missing/wrong password rejection
- PDF images embedded in DOCX
- Scanned PDF OCR to editable DOCX
- Scanned PDF OCR to editable XLSX
- DOCX to PDF using local LibreOffice

Skipped:
- Desktop UI import test, because PySide6 is not installed in this Linux environment.
  The Windows GitHub Actions build installs PySide6, so this test will run there.

## Fixes made in this revision
- Corrected Inno Setup AppId escaping.
- Added a branded application icon and installer icon.
- Added PDF password prompts, including separate prompts for protected files in a batch.
- Added password-aware PDF extraction for Word and Excel outputs.
- Added embedded PDF image extraction into DOCX where possible.
- Improved PDF-to-Excel fallback: native text is used before OCR.
- Added PDFium dependency for scanned-page rendering.
- Added page-range validation and clearer OCR language-data errors.
- Isolated LibreOffice temporary profiles to reduce process conflicts.
- Updated Windows batch build to run tests, package OCR files, and compile Inno Setup.
- Updated PowerShell and GitHub Actions build scripts.
- Added automated conversion, OCR, password, image, and UI-import tests.

## Windows build target
Windows 10 and Windows 11, 64-bit (x64), using a native Windows runner.

## Final release checks still required
1. Run the GitHub Actions workflow from the project's GitHub repository.
2. Confirm the PyInstaller build succeeds.
3. Confirm Inno Setup creates `OneGrafix_PDF_Converter_Setup.exe`.
4. Install and launch on clean Windows 10 x64 and Windows 11 x64 machines.
5. Disconnect the network and verify OCR still works.
6. Verify Word/Excel-to-PDF on a machine with LibreOffice installed.
7. Review third-party licence obligations and digitally sign the installer before distribution.

## Product limitations
- Complex PDF layout reconstruction is not pixel-perfect.
- OCR-derived table columns are approximate; check financial and numeric values.
- LibreOffice is not bundled. It must be installed separately for Word/Excel-to-PDF.
- Batch processing cannot yet be cancelled while running.
