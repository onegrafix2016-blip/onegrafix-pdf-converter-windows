#define MyAppName "OneGrafix PDF Converter"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "OneHost Digital"
#define MyAppExeName "OneGrafix PDF Converter.exe"

[Setup]
AppId={{8E6B16D7-ACF1-4E3E-9E93-0A1E6A7F1001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
MinVersion=10.0
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
DisableProgramGroupPage=yes
DefaultDirName={autopf}\OneGrafix PDF Converter
DefaultGroupName={#MyAppName}
OutputDir=Output
OutputBaseFilename=OneGrafix_PDF_Converter_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=..\assets\onegrafix.ico

[Files]
Source: "..\dist\OneGrafix PDF Converter\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\runtime\tesseract\*"; DestDir: "{app}\runtime\tesseract"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: postinstall nowait skipifsilent
