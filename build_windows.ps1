$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== OneGrafix PDF Converter Windows Build ===" -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python 3.11 x64 is required. Install it from python.org."
}
if (-not (Test-Path "runtime\tesseract\tesseract.exe")) {
    throw "Copy the complete Tesseract OCR folder into runtime\tesseract first."
}
if (-not (Test-Path "runtime\tesseract\tessdata\eng.traineddata")) {
    throw "English OCR data is missing: runtime\tesseract\tessdata\eng.traineddata"
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
}
& ".venv\Scripts\python.exe" -m pip install --upgrade pip
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller

& ".venv\Scripts\python.exe" -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Automated conversion tests failed." }

& ".venv\Scripts\pyinstaller.exe" --noconfirm --clean --windowed `
    --name "OneGrafix PDF Converter" --icon "assets\onegrafix.ico" `
    --collect-all fitz `
    --collect-all pdfplumber `
    --collect-all pypdfium2 `
    --collect-all PySide6 `
    --collect-all pytesseract `
    app.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

Copy-Item "runtime" "dist\OneGrafix PDF Converter\runtime" -Recurse -Force

$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) { $iscc = "$env:ProgramFiles\Inno Setup 6\ISCC.exe" }
if (-not (Test-Path $iscc)) { throw "Install Inno Setup 6 before compiling the installer." }

Push-Location "installer"
& $iscc "OneGrafixPDFConverter.iss"
$compileExit = $LASTEXITCODE
Pop-Location
if ($compileExit -ne 0) { throw "Inno Setup compilation failed." }

Write-Host "Build complete. Installer is in installer\Output." -ForegroundColor Green
