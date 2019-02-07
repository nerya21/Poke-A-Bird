#define MyAppName "Poke-A-Bird Prerequisites"
#define MyAppVersion "0.6"
#define MyAppPublisher "Elad Yacovi and Nerya Meshulam, Tel Aviv University"
#define MyAppURL "https://github.com/nerya21/Poke-A-Bird"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{38E0C05C-2A59-4D95-BE8B-7C307C1A777C}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
;AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}   
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
CreateAppDir=no
OutputBaseFilename=poke-a-bird_prerequisites_{#MyAppVersion}
Compression=lzma
SolidCompression=yes
Uninstallable = no
DisableWelcomePage=no
AppCopyright=Copyright (C) 2018-2019 {#MyAppPublisher}
ChangesEnvironment=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: ".\bin\*.*"; DestDir: "{tmp}"; Flags: ignoreversion
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Run]
Filename: "{tmp}\python-3.7.1.exe"; Parameters: "/quiet Include_launcher=0"; StatusMsg: "Installing Python (python-3.7.1.exe)...";
Filename: "{tmp}\install_packages.bat"; Parameters:{tmp} ; StatusMsg: "Installing Python packages (install_packages.bat)..."; 
Filename: "{tmp}\vlc-3.0.6-win32.exe"; Parameters: "/S"; StatusMsg: "Installing VLC (vlc-3.0.6-win32.exe)...";
Filename: "https://github.com/nerya21/Poke-A-Bird/releases"; Description: "Visit Poke-A-Bird website"; Flags: postinstall shellexec runasoriginaluser