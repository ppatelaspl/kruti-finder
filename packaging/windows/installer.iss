; Inno Setup script - builds "KrutiFinder-Setup-<version>.exe" from dist\KrutiFinder.
;   iscc /DMyAppVersion=1.0.0 packaging\windows\installer.iss
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif

[Setup]
AppId={{6C7B2E4A-8F1D-4B7C-9E2A-5D3F1A0B9C71}
AppName=Kruti Finder
AppVersion={#MyAppVersion}
AppPublisher=Aspire Softserv Pvt. Ltd.
DefaultDirName={autopf}\Kruti Finder
DefaultGroupName=Kruti Finder
DisableProgramGroupPage=yes
; Installs for the current user without admin rights; admins can choose "all users".
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir=..\..\dist\installers
OutputBaseFilename=KrutiFinder-Setup-{#MyAppVersion}
SetupIconFile=..\..\app\assets\icon.ico
UninstallDisplayIcon={app}\KrutiFinder.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\..\dist\KrutiFinder\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Kruti Finder"; Filename: "{app}\KrutiFinder.exe"
Name: "{group}\Uninstall Kruti Finder"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Kruti Finder"; Filename: "{app}\KrutiFinder.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\KrutiFinder.exe"; Description: "Launch Kruti Finder"; Flags: nowait postinstall skipifsilent
