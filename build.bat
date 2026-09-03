@echo off
REM Windows용 .exe 빌드 스크립트. 이 파일은 Windows PC에서 실행해야 합니다.

python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt
pip install pyinstaller

pyinstaller --onefile --noconsole --name QRcode main.py

echo.
echo 빌드 완료: dist\QRcode.exe
echo config.json 파일을 dist 폴더에 복사한 뒤 학생들에게 두 파일(QRcode.exe, config.json)을 함께 배포하세요.
pause
