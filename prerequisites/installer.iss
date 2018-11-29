#define MyAppName "Poke-A-Bird Prerequisites"
#define MyAppVersion "0.3"
#define MyAppPublisher "Elad Yacovi and Nerya Meshulam, Tel Aviv University"
#define MyAppURL "https://github.com/nerya21/Poke-A-Bird"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{D82C6B78-FD9F-45C6-9F25-89B65C4024D8}}
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
AppCopyright=Copyright (C) 2018 {#MyAppPublisher}
ChangesEnvironment=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: ".\bin\*.*"; DestDir: "{tmp}"; Flags: ignoreversion
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Run]
Filename: "{tmp}\python-3.7.1.exe"; Parameters: "/quiet Include_launcher=0"; StatusMsg: "Installing Python (python-3.7.1.exe)...";
Filename: "{localappdata}\Programs\Python\Python37-32\Scripts\pip3"; WorkingDir: "{localappdata}\Programs\Python\Python37-32"; Parameters: "-q --disable-pip-version-check install {tmp}\Pillow-5.3.0-cp37-cp37m-win32.whl"; StatusMsg: "Installing Python packages (Pillow-5.3.0-cp37-cp37m-win32.whl)..."; 
Filename: "{localappdata}\Programs\Python\Python37-32\Scripts\pip3"; WorkingDir: "{localappdata}\Programs\Python\Python37-32"; Parameters: "-q --disable-pip-version-check install {tmp}\python-vlc-3.0.4106.tar.gz"; StatusMsg: "Installing Python packages (python-vlc-3.0.4106.tar.gz)..."; 
Filename: "{localappdata}\Programs\Python\Python37-32\Scripts\pip3"; WorkingDir: "{localappdata}\Programs\Python\Python37-32"; Parameters: "-q --disable-pip-version-check install {tmp}\pyttk-0.3.2.tar.gz"; StatusMsg: "Installing Python packages (pyttk-0.3.2.tar.gz)..."; 
Filename: "{localappdata}\Programs\Python\Python37-32\Scripts\pip3"; WorkingDir: "{localappdata}\Programs\Python\Python37-32"; Parameters: "-q --disable-pip-version-check install {tmp}\Pmw-2.0.1.tar.gz"; StatusMsg: "Installing Python packages (Pmw-2.0.1.tar.gz)..."; 
Filename: "{tmp}\vlc-3.0.4-win32.exe"; Parameters: "/S"; StatusMsg: "Installing VLC (vlc-3.0.4-win32.exe)...";
Filename: "https://github.com/nerya21/Poke-A-Bird/releases"; Description: "Visit Poke-A-Bird website"; Flags: postinstall shellexec runasoriginaluser