; Inno Setup script of the Windows installer of beam_calculator.
; It packs the app folder PyInstaller built (dist\beam_calculator\); run it
; through packaging\build_windows.ps1, or by hand from the repository root:
;   iscc /DAppVersion=0.1.0 packaging\windows\beam_calculator.iss
; Keep this file as UTF-8 with BOM: without it Inno Setup misreads the accents.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "beam_calculator"
#define AppExe AppName + ".exe"
#define RepoDir AddBackslash(SourcePath) + "..\.."

[Setup]
; Fixed forever: Windows recognizes a newer installer as an update through it
AppId={{04BB7EC5-4A95-41BC-812A-1443A4CE0C27}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Artur Kalil Corrêa
AppPublisherURL=https://github.com/arturkcorr3a/beam_calculator
; Per-user install (%LOCALAPPDATA%\Programs\beam_calculator): no administrator
; password, and the app's folder stays writable by its user
PrivilegesRequired=lowest
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
LicenseFile={#RepoDir}\LICENSE
SetupIconFile={#RepoDir}\resources\logo\png\icon\app.ico
UninstallDisplayIcon={app}\{#AppExe}
OutputDir={#RepoDir}\dist
OutputBaseFilename={#AppName}-Setup-{#AppVersion}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
; An update replaces the bundle as a whole: files the new version no longer has
; must not linger next to the ones it brings
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#RepoDir}\dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
