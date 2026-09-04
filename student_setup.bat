@echo off
chcp 65001 >nul
REM ============================================================
REM  퇴실 QR코드 프로그램 - 학생용 설치 스크립트
REM  더블클릭 한 번으로 설치 + Windows 시작프로그램 등록까지 완료합니다.
REM ============================================================

echo.
echo [1/4] Python 설치 확인 중...
where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo [오류] Python이 설치되어 있지 않습니다.
    echo https://www.python.org/downloads/ 에서 Python을 설치한 뒤
    echo 설치 화면에서 "Add python.exe to PATH"를 꼭 체크하고 다시 실행해주세요.
    echo.
    pause
    exit /b 1
)
echo     -> OK

echo.
echo [2/4] 가상환경 준비 중... (시간이 걸릴 수 있습니다)
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate.bat

echo.
echo [3/4] 필요한 패키지 설치 중...
python -m pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo [오류] 패키지 설치에 실패했습니다. 인터넷 연결을 확인해주세요.
    pause
    exit /b 1
)
echo     -> OK

echo.
echo [4/4] Windows 시작프로그램 등록 중...
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
copy /Y "%~dp0run_silent.vbs" "%STARTUP_DIR%\qrcode-checkout.vbs" >nul
echo     -> 등록 완료: 다음 부팅부터 자동으로 대기 상태가 됩니다.

echo.
echo ============================================================
echo  설치가 완료되었습니다!
echo  지금 바로 테스트해보시겠습니까? (QR을 즉시 한 번 띄워봅니다)
echo ============================================================
set /p RUN_TEST="테스트 실행 (Y/N): "
if /i "%RUN_TEST%"=="Y" (
    python main.py --test-now
)

echo.
echo 컴퓨터를 재부팅하면 프로그램이 자동으로 백그라운드에서 대기합니다.
echo 지금 바로 대기 상태로 실행하려면 run_silent.vbs를 더블클릭하세요.
pause
