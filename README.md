# 퇴실 QR코드 자동 표시 프로그램

부트캠프 퇴실 체크를 깜빡하는 사람이 없도록, 정해진 시간이 되면 퇴실용 QR코드를
컴퓨터 화면에 전체화면으로 띄워주는 프로그램입니다.

QR은 매주 바뀌므로, **관리자(본인)가 GitHub Gist 한 곳만 갱신하면 설치된 모든 학생
PC가 자동으로 새 QR을 받아갑니다.** 학생 PC에서는 별도 작업이 필요 없습니다.

## 동작 구조

```
[관리자 PC] admin_update.py (비밀번호 인증) --> GitHub Gist(JSON) 갱신
                                                     |
                                                     v (5분마다 자동 조회)
[학생 PC 1..N] main.py --> Gist에서 checkout_url / checkout_time을 읽어와 캐시(cache.json)
                            --> 정해진 시각에 QR 전체화면 표시
```

- 학생 PC가 오프라인이거나 Gist 조회에 실패해도 마지막으로 받아온 `cache.json` 값으로 계속 동작합니다.
- Gist는 **공개(public)** 로 만들어도 되며, 읽기는 누구나 가능하지만 **쓰기(갱신)** 는 GitHub 토큰이 있어야 하므로 관리자만 QR을 바꿀 수 있습니다.

---

## 1. 최초 설정 (관리자 1회만)

### 1-1. GitHub Gist 생성
1. https://gist.github.com/ 접속 (본인 GitHub 계정으로 로그인)
2. 파일 이름: `bootcamp_qr_config.json`
3. 내용:
   ```json
   {
     "checkout_url": "https://실제-퇴실-QR-주소",
     "checkout_time": "18:00"
   }
   ```
4. **Create public gist** 클릭
5. 생성된 Gist의 URL에서 Gist ID를 확인 (예: `https://gist.github.com/내아이디/abcdef1234567890` → ID는 `abcdef1234567890`)
6. "Raw" 버튼을 눌러 나오는 주소를 복사 (`https://gist.githubusercontent.com/.../raw/bootcamp_qr_config.json` 형태)

### 1-2. GitHub 토큰 발급 (Gist 갱신용)
1. https://github.com/settings/tokens → **Generate new token (classic)**
2. 권한(scope)에서 `gist` 만 체크
3. 생성된 토큰을 안전한 곳에 보관 (다시 볼 수 없으니 주의)

### 1-3. 파이썬 환경 준비
```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 1-4. 학생 배포용 `config.json` 작성
`sync_url`에 위에서 복사한 Raw 주소를 넣습니다. `checkout_url`/`checkout_time`은
Gist 조회가 실패할 때만 쓰이는 예비값이라 대략 맞춰두면 됩니다.

```json
{
  "sync_url": "https://gist.githubusercontent.com/내아이디/GIST_ID/raw/bootcamp_qr_config.json",
  "fetch_interval_seconds": 300,
  "checkout_url": "https://실제-퇴실-QR-주소",
  "checkout_time": "18:00",
  "display_seconds": 600,
  "window_title": "퇴실 QR코드 - 스캔 후 아무 키나 눌러 닫기"
}
```

이 `config.json`, `main.py`, `requirements.txt` (또는 exe로 빌드한 실행파일)만
학생들에게 배포하면 됩니다. **`admin_update.py`와 `admin_config.json`은 절대
학생에게 배포하지 마세요.**

---

## 2. 학생 PC에서 실행

```bash
python3 main.py
```

매일 Gist에 등록된 시각에 자동으로 QR이 전체화면으로 뜹니다. 종료는 `Ctrl+C`.
바로 테스트하려면:

```bash
python3 main.py --test-now
```

### 부팅 시 자동 실행 (선택)
- **Windows**: `pyinstaller --onefile --noconsole main.py` 로 exe 생성 → `config.json`을
  같은 폴더에 두고 → `Win+R` → `shell:startup` → 폴더에 exe 바로가기 추가
- **macOS**: 로그인 항목(시스템 설정 > 일반 > 로그인 항목)에 `python3 main.py` 실행
  스크립트 등록, 또는 `launchd` 사용

---

## 3. 관리자: 매주 QR 갱신하기

관리자 PC에서만 실행합니다.

```bash
source venv/bin/activate
python3 admin_update.py
```

- 최초 실행 시 관리자 비밀번호를 설정합니다 (6자 이상).
- 이후 실행할 때마다 비밀번호를 확인한 뒤, Gist ID / 파일명 / GitHub 토큰을 물어봅니다
  (한 번 입력하면 `admin_config.json`에 로컬 저장되어 다음부터는 비밀번호만 입력하면 됩니다).
- 새 퇴실 QR URL과 (필요하면) 시각을 입력하면 Gist가 즉시 갱신됩니다.
- 학생 PC들은 각자의 `fetch_interval_seconds`(기본 5분) 주기로 자동 반영됩니다.

명령줄 인자로 바로 갱신할 수도 있습니다:

```bash
python3 admin_update.py --url "https://새로운-퇴실-QR-주소" --time "18:00"
```

### 비밀번호 재설정
```bash
python3 admin_update.py --set-password
```

### 보안 주의사항
- `admin_config.json`에는 비밀번호 해시와 (저장했다면) GitHub 토큰이 들어있습니다.
  **git에 커밋하거나 학생에게 공유하지 마세요** (`.gitignore`에 이미 제외되어 있습니다).
- GitHub 토큰은 `gist` 권한만 부여하세요.

---

## 4. 배포용 exe 빌드 (선택)

학생들에게 Python 설치 없이 나눠주고 싶다면 PyInstaller로 실행파일을 만듭니다.

**중요: PyInstaller는 빌드를 실행한 운영체제용 실행파일만 만듭니다 (크로스 컴파일 불가).**
학생들 대부분이 Windows를 쓴다면 **Windows PC에서** `build.bat`을 실행해야 진짜 `.exe`가 나옵니다.
macOS에서 빌드하면 macOS용 실행파일(`.app`)만 만들어지고 Windows에서는 실행되지 않습니다.

### Windows에서 빌드 (.exe)
Windows PC에서 이 프로젝트 폴더를 열고:
```
build.bat
```
더블클릭하거나 명령 프롬프트에서 실행하면 `dist\QRcode.exe`가 생성됩니다.

### macOS/Linux에서 빌드 (해당 OS용, 배포는 보통 필요 없음)
```bash
./build.sh
```

### 배포
빌드가 끝나면 `dist` 폴더의 실행파일과 `config.json`을 함께 전달하세요.
(`admin_update.py`, `admin_config.json`은 포함하지 않습니다.)
