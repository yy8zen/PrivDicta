; Inno Setup のスクリプト。GitHub Actions の Windows ジョブから次のように呼ぶ。
;   iscc /DAppVersion=0.1.0 packaging\windows\installer.iss
; 管理者権限なしで、利用者のフォルダにインストールする。

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6A0F3C5E-2B7D-4E8A-9C1F-5D3B7A9E2C41}
AppName=moonshine-dictate
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\moonshine-dictate
DefaultGroupName=moonshine-dictate
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\..\dist
OutputBaseFilename=moonshine-dictate-{#AppVersion}-windows-setup
Compression=lzma2/max
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\..\LICENSE

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Files]
Source: "..\..\dist\moonshine-dictate\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\moonshine-dictate"; Filename: "{app}\moonshine-dictate.exe"

[Run]
Filename: "{app}\moonshine-dictate.exe"; Description: "moonshine-dictate を起動する"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\moonshine-dictate.exe"; Parameters: "quit"; Flags: runhidden skipifdoesntexist; RunOnceId: "QuitApp"
