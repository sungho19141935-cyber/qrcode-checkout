# 퇴실 QR코드 프로그램 - 학생용 제거 스크립트
# 사용법: irm https://qrcode-checkout.vercel.app/uninstall.ps1 | iex

$procs = Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' or Name='python.exe'" |
  Where-Object { $_.CommandLine -like '*qrcode-checkout*' }
$procs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
$procs | ForEach-Object { Wait-Process -Id $_.ProcessId -Timeout 10 -ErrorAction SilentlyContinue }

Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\qrcode-checkout.vbs" -Force -ErrorAction SilentlyContinue

$installDir = "$env:LOCALAPPDATA\qrcode-checkout"
for ($i = 0; $i -lt 5; $i++) {
    if (-not (Test-Path $installDir)) { break }
    Remove-Item $installDir -Recurse -Force -ErrorAction SilentlyContinue
    if (-not (Test-Path $installDir)) { break }
    Start-Sleep -Seconds 1
}

if (Test-Path $installDir) {
    Write-Host "일부 파일이 아직 사용 중이라 삭제하지 못했습니다. 컴퓨터를 재부팅한 뒤 이 명령어를 다시 실행해주세요."
} else {
    Write-Host "삭제 완료: 퇴실 QR코드 프로그램이 제거되었습니다."
}
