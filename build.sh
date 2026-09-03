#!/bin/bash
# macOS/Linux용 빌드 스크립트. 이 스크립트로 만든 실행파일은 Windows에서 동작하지 않습니다.
# Windows .exe가 필요하면 build.bat을 Windows PC에서 실행하세요.
set -e

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller

pyinstaller --onefile --windowed --name QRcode main.py

echo
echo "빌드 완료: dist/QRcode"
echo "config.json 파일을 dist 폴더에 복사한 뒤 학생들에게 함께 배포하세요."
