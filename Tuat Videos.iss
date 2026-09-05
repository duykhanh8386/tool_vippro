#define MyAppName "Tuất Videos"
#ifndef MyAppVersion
  #define MyAppVersion "1.1.5"
#endif
#define MyAppExeName "Tuat Videos.exe"
#define MyAppInstallName "Tuat Videos 7F47B95D"

#ifndef BuildSourceDir
  #define BuildSourceDir "dist\Tuat Videos"
#endif

#ifndef BuildOutputDir
  #define BuildOutputDir "installer_dist"
#endif

[Setup]
AppId={{7F47B95D-6FD8-4A87-B2F8-9B0CE6A91D42}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
DefaultDirName={localappdata}\Programs\{#MyAppInstallName}
DefaultGroupName={#MyAppInstallName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#BuildOutputDir}
OutputBaseFilename=TuatVideos_Setup
SetupIconFile=assets\logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
VersionInfoVersion={#MyAppVersion}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[InstallDelete]
; Remove the previous packaged runtime so stale optional Python modules cannot
; survive an upgrade. User databases and settings live under AppData and are
; intentionally not touched here.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#BuildSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppInstallName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppInstallName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Flags: nowait skipifsilent
