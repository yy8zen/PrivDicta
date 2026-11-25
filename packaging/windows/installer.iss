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
; ライセンス全文、帰属表示、使い方をインストール先の直下にも置く（要件 R7.2）
Source: "..\..\docs\user-guide.md"; DestDir: "{app}"; DestName: "使い方.md"
Source: "..\NOTICE.txt"; DestDir: "{app}"
Source: "..\MOONSHINE-LICENSE.txt"; DestDir: "{app}"
Source: "..\..\LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"

[Icons]
Name: "{group}\moonshine-dictate"; Filename: "{app}\moonshine-dictate.exe"
Name: "{group}\moonshine-dictate の使い方"; Filename: "{app}\使い方.md"

[Registry]
; 設定の「ログインしたときに自動で起動する」が書いた値を、アンインストール時に消す
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "moonshine-dictate"; Flags: uninsdeletevalue dontcreatekey

[Run]
Filename: "{app}\moonshine-dictate.exe"; Description: "moonshine-dictate を起動する"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\moonshine-dictate.exe"; Parameters: "quit"; Flags: runhidden skipifdoesntexist; RunOnceId: "QuitApp"
