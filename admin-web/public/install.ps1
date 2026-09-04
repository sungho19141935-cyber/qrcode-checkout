# 퇴실 QR코드 프로그램 - 학생용 원클릭 설치 스크립트
# 사용법: PowerShell에서 아래 한 줄만 실행
#   irm https://raw.githubusercontent.com/sungho19141935-cyber/qrcode-checkout/main/install.ps1 | iex

$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$RepoRaw = "https://raw.githubusercontent.com/sungho19141935-cyber/qrcode-checkout/main"
$InstallDir = Join-Path $env:LOCALAPPDATA "qrcode-checkout"
$Files = @("main.py", "requirements.txt", "config.json")

function Write-Step($msg) {
    Write-Host ""
    Write-Host $msg -ForegroundColor Cyan
}

Write-Step "[1/5] 설치 폴더 준비 중... ($InstallDir)"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

Write-Step "[2/5] 최신 프로그램 파일 다운로드 중..."
foreach ($f in $Files) {
    $dest = Join-Path $InstallDir $f
    if ($f -eq "config.json" -and (Test-Path $dest)) {
        # config.json은 이미 있으면 덮어쓰지 않음 (재설치/업데이트 시 기존 설정 보존)
        continue
    }
    Invoke-WebRequest -Uri "$RepoRaw/$f" -OutFile $dest -UseBasicParsing
}

Write-Step "[3/5] Python 설치 확인 중..."
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host ""
    Write-Host "[오류] Python이 설치되어 있지 않습니다." -ForegroundColor Red
    Write-Host "https://www.python.org/downloads/ 에서 Python을 설치한 뒤" -ForegroundColor Yellow
    Write-Host "설치 화면에서 'Add python.exe to PATH'를 꼭 체크하고 이 명령어를 다시 실행해주세요." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "아무 키나 누르면 종료합니다"
    exit 1
}
Write-Host "    -> OK"

Write-Step "[4/5] 가상환경 및 패키지 설치 중... (시간이 걸릴 수 있습니다)"
Push-Location $InstallDir
if (-not (Test-Path "venv")) {
    python -m venv venv
}
& ".\venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
& ".\venv\Scripts\pip.exe" install --quiet -r requirements.txt
Pop-Location
Write-Host "    -> OK"

Write-Step "[5/5] Windows 시작프로그램 등록 중..."
$vbsPath = Join-Path $InstallDir "run_silent.vbs"
@"
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = scriptDir & "\venv\Scripts\pythonw.exe"
mainPy = scriptDir & "\main.py"
shell.CurrentDirectory = scriptDir
shell.Run """" & pythonw & """ """ & mainPy & """", 0, False
"@ | Set-Content -Path $vbsPath -Encoding ASCII

$startupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
Copy-Item -Path $vbsPath -Destination (Join-Path $startupDir "qrcode-checkout.vbs") -Force
Write-Host "    -> 등록 완료: 다음 부팅부터 자동으로 대기 상태가 됩니다."

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " 설치가 완료되었습니다!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "지금 바로 백그라운드 대기를 시작합니다..."
Start-Process -FilePath "wscript.exe" -ArgumentList "`"$vbsPath`""
Write-Host "완료! 컴퓨터를 재부팅해도 자동으로 다시 시작됩니다."
