; Inno Setup 스크립트: 학생용 퇴실 QR 프로그램 설치 마법사
; GitHub Actions(windows-latest)에서 ISCC.exe로 컴파일됨

[Setup]
AppId={{9C6E6B9B-3F1E-4E0B-9C77-5B1F0B3F6D21}}
AppName=퇴실 QR 표시 프로그램
AppVersion=1.0
AppPublisher=Bootcamp QRcode
DefaultDirName={userpf}\QRcode
DefaultGroupName=퇴실 QR 표시 프로그램
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=installer_output
OutputBaseFilename=QRcodeSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\QRcode.exe

[Tasks]
Name: "startup"; Description: "Windows 시작 시 자동 실행 (부팅하면 자동으로 대기 시작)"; GroupDescription: "추가 옵션:"; Flags: checkedonce

[Files]
Source: "dist\QRcode.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.json"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\퇴실 QR 표시 프로그램"; Filename: "{app}\QRcode.exe"
Name: "{group}\제거"; Filename: "{uninstallexe}"
Name: "{userstartup}\퇴실 QR 표시 프로그램"; Filename: "{app}\QRcode.exe"; Tasks: startup

[Run]
Filename: "{app}\QRcode.exe"; Description: "설치 후 지금 바로 실행"; Flags: nowait postinstall skipifsilent unchecked
