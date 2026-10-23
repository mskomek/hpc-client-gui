#ifndef AppVersion
#define AppVersion "1.5.9"
#endif
#ifndef AppGuid
#ifdef AcceptanceMachineIdentity
#define AppGuid "{C78C4C38-6D59-4429-8F66-6DFD3CB33D7A}"
#else
#ifdef AcceptanceIdentity
#define AppGuid "{6EB4B606-42E5-4BC5-BEE8-75B961115CE1}"
#else
#define AppGuid "{B1EF0D52-154D-47A6-9A49-5D3C530D8B0E}"
#endif
#endif
#endif
#ifndef ProductName
#ifdef AcceptanceMachineIdentity
#define ProductName "HPC Client GUI Machine Acceptance"
#else
#ifdef AcceptanceIdentity
#define ProductName "HPC Client GUI Acceptance"
#else
#define ProductName "HPC Client GUI"
#endif
#endif
#endif

[Setup]
AppId={{#AppGuid}
AppName={#ProductName}
AppVersion={#AppVersion}
AppVerName={#ProductName} {#AppVersion}
AppPublisher=Mehmed Sinan Komek
AppPublisherURL=https://github.com/mskomek/hpc-client-gui
AppSupportURL=https://github.com/mskomek/hpc-client-gui/issues
AppUpdatesURL=https://github.com/mskomek/hpc-client-gui/releases
DefaultDirName={autopf}\{#ProductName}
DefaultGroupName={#ProductName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UsePreviousPrivileges=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
SetupIconFile=hpc-client-gui.ico
LicenseFile=..\..\LICENSE
OutputDir=..\..\dist\installer
OutputBaseFilename=hpc-client-gui-setup-{#AppVersion}-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
UninstallDisplayName={#ProductName}
UninstallDisplayIcon={app}\hpc-client-gui.exe
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\..\dist\hpc-client-gui\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\dist\hpc-client-cli\hpc-client-cli.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#ProductName}"; Filename: "{app}\hpc-client-gui.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\{#ProductName}"; Filename: "{app}\hpc-client-gui.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\hpc-client-gui.exe"; Description: "Launch {#ProductName}"; WorkingDir: "{app}"; Flags: postinstall nowait skipifsilent
