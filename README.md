# OneGrafix PDF Converter

Windows desktop application source package by OneHost Digital.

## Features implemented in this build
- PDF to editable DOCX text, with extracted PDF images embedded where possible
- Offline OCR fallback for scanned PDF pages
- PDF tables to XLSX worksheets
- OCR fallback for scanned PDF pages to editable Excel rows/cells using approximate whitespace column detection
- PDFium rendering dependency for scanned-page OCR-to-Excel
- DOCX/DOC and XLSX/XLS to PDF through local LibreOffice
- Multi-file batch conversion with per-file PDF password prompts
- PDF page range selection (for example `1-3,5`)
- PDF password entry for protected PDF-to-Word and PDF-to-Excel conversion
- Selectable output folder
- Windows PyInstaller and Inno Setup build scripts
- Local processing; no cloud conversion APIs

## Known limitations
- PDF is a fixed-layout format. Complex page layouts, columns, fonts, and exact image placement are not reconstructed perfectly in Word.
- OCR table extraction uses approximate visual whitespace to infer columns. Always verify figures and column alignment, especially in financial documents.
- Password-protected PDFs can be processed when the correct password is supplied. Batch conversion prompts separately for each protected file.
- Batch processing is sequential and cannot yet be cancelled mid-job. If a later file fails, earlier converted files remain in the output folder.
- Office-to-PDF requires LibreOffice installed on the computer. The installer does not bundle LibreOffice.
- Legacy `.doc` and `.xls` support depends on LibreOffice's import filters.

## Build prerequisites
- Windows 10 and Windows 11, both 64-bit (one x64 build target)
- Python 3.11
- Tesseract OCR with `eng.traineddata`
- LibreOffice (for Word/Excel to PDF)
- Inno Setup 6

## Run from source
1. Install Python 3.11.
2. Copy the Tesseract installation directory into `runtime\\tesseract\\` (must contain `tesseract.exe` and `tessdata\\eng.traineddata`).
3. Run `run_app.bat`.
4. Install LibreOffice for Office-to-PDF support.

## Build Windows installer
1. Run `run_app.bat` once to install dependencies.
2. Ensure `runtime\\tesseract\\` contains the complete Tesseract runtime and English data.
3. Run `build_windows.bat`. It runs the tests, builds the app, copies OCR runtime files, and compiles the installer when Inno Setup 6 is installed.
4. The installer output will be created under `installer\\Output\\`.

This is source code and build configuration, not a compiled or tested Windows installer.


## Windows compatibility target
This project targets Windows 10 64-bit and Windows 11 64-bit using one x64
application build. The Inno Setup script restricts installation to x64 Windows
and declares Windows 10 as the minimum OS. Windows 10 support is subject to the
machine having a supported update level and required Microsoft runtime components.
Build and test the installer on clean Windows 10 and Windows 11 virtual machines
before distributing it.


## Automated Windows build (recommended)
The repository now includes a GitHub Actions workflow at
`.github/workflows/windows-build.yml`. It builds on a native Windows x64 runner,
installs Tesseract and Inno Setup, runs conversion smoke tests, compiles the app,
and uploads the installer as a workflow artifact.

To use it:
1. Create a private or public GitHub repository.
2. Upload the contents of this project folder to the repository.
3. Open the repository's **Actions** tab.
4. Select **Build OneGrafix PDF Converter for Windows**.
5. Choose **Run workflow**.
6. When complete, open the workflow run and download the
   `OneGrafix-PDF-Converter-Windows-x64` artifact.

A local Windows build script is also supplied as `build_windows.ps1`.
The GitHub workflow is not executed by this project package itself; it must be
run from the user's GitHub repository. Inspect the generated artifact and test
the installer on clean Windows 10 and Windows 11 x64 machines before release.


## Important release notes
- The Windows installer includes Tesseract OCR and English language data.
- LibreOffice is not bundled. Install LibreOffice on the target computer to use Word/Excel-to-PDF.
- The app's PDF-to-Word reconstruction is editable and embeds extracted images, but it does not promise exact reproduction of complex PDF layouts or preserve all fonts, columns, and table geometry.
- PDF-to-Excel uses detected PDF tables first. If no table is detected, it exports native text or OCR-recognised lines. OCR column detection is approximate; verify all numeric values.
- The app does not upload files or call cloud conversion APIs.
