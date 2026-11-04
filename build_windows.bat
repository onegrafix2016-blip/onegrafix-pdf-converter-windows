@echo off
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
  echo Run run_app.bat first to create the virtual environment and install dependencies.
  pause
  exit /b 1
)
if not exist runtime\tesseract\tesseract.exe (
  echo ERROR: runtime\tesseract\tesseract.exe not found.
  echo Copy the full Tesseract installation folder into runtime\tesseract.
  pause
  exit /b 1
)
if not exist runtime\tesseract\tessdata\eng.traineddata (
  echo ERROR: English OCR data is missing.
  pause
  exit /b 1
)

call .venv\Scripts\activate
python -m unittest discover -s tests -v
if errorlevel 1 (
  echo Automated tests failed. Build stopped.
  pause
  exit /b 1
)

pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --name "OneGrafix PDF Converter" --icon assets\onegrafix.ico ^
  --collect-all fitz --collect-all pdfplumber --collect-all pypdfium2 --collect-all PySide6 ^
  --collect-all pytesseract app.py
if errorlevel 1 (
  echo PyInstaller build failed.
  pause
  exit /b 1
)

if exist "dist\OneGrafix PDF Converter\runtime" rmdir /s /q "dist\OneGrafix PDF Converter\runtime"
xcopy runtime "dist\OneGrafix PDF Converter\runtime" /E /I /Y >nul
if errorlevel 1 (
  echo Failed to copy OCR runtime into the application.
  pause
  exit /b 1
)

set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
  echo Inno Setup 6 was not found. Install it, then run this script again.
  pause
  exit /b 1
)

pushd installer
"%ISCC%" OneGrafixPDFConverter.iss
if errorlevel 1 (
  popd
  echo Inno Setup compilation failed.
  pause
  exit /b 1
)
popd

echo.
echo BUILD SUCCESSFUL.
echo Installer: installer\Output\OneGrafix_PDF_Converter_Setup.exe
pause
