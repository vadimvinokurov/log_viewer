; Inno Setup Script for Log Viewer
; Ref: docs/specs/features/windows-startup-optimization.md §3.2.2
; Master: docs/SPEC.md §1

#define AppName "Log Viewer"
#define AppVersion "0.1.0"
#define AppPublisher "Log Viewer Team"
#define AppURL "https://github.com/..."
#define AppExeName "LogViewer.exe"

[Setup]
AppId={{8A7D9B3C-1234-5678-9ABC-DEF012345678}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
; NOTE: LICENSE file must be created before building installer
; LicenseFile=LICENSE
OutputDir=dist
OutputBaseFilename=LogViewer-{#AppVersion}-windows-setup
SetupIconFile=build\icons\app.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Copy all files from PyInstaller onedir build
; Ref: docs/specs/features/windows-startup-optimization.md §3.2.1
Source: "dist\LogViewer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:ProgramOnTheWeb,{#AppName}}"; Filename: "{#AppURL}"
Name: "{group}\{cm:UninstallShortcut,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Registry]
; File association for .log files
; Ref: docs/specs/features/file-association.md
Root: HKCR; Subkey: ".log"; ValueType: string; ValueName: ""; ValueData: "LogFile"; Flags: uninsdeletevalue
Root: HKCR; Subkey: "LogFile"; ValueType: string; ValueName: ""; ValueData: "Log File"; Flags: uninsdeletekey
Root: HKCR; Subkey: "LogFile\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExeName},0"
Root: HKCR; Subkey: "LogFile\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""