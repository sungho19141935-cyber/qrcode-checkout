# 퇴실 QR코드 프로그램 - 학생용 제거 스크립트
# 사용법: irm https://qrcode-checkout.vercel.app/uninstall.ps1 | iex

Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" |
  Where-Object { $_.CommandLine -like '*qrcode-checkout*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\qrcode-checkout.vbs" -Force -ErrorAction SilentlyContinue
Remove-Item "$env:LOCALAPPDATA\qrcode-checkout" -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "삭제 완료: 퇴실 QR코드 프로그램이 제거되었습니다."
