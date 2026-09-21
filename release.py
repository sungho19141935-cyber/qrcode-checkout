"""배포용 version.json을 생성한다.

main.py를 고쳐 학생 PC에 배포하려면:

    1. main.py의 VERSION을 올린다
    2. python release.py
    3. main.py와 version.json을 함께 커밋 & 푸시

학생 프로그램은 1시간마다 version.json을 확인해서, 버전이 다르면 main.py를
내려받아 체크섬/문법/실행 검증을 모두 통과한 경우에만 교체하고 재시작한다.

version.json의 "enabled"를 false로 바꾸고 푸시하면 전체 자동 업데이트가 즉시
멈춘다 (잘못된 버전을 내보냈을 때의 비상 스위치).
"""

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
MAIN_PY = ROOT / "main.py"
VERSION_JSON = ROOT / "version.json"
RAW_BASE = "https://raw.githubusercontent.com/sungho19141935-cyber/qrcode-checkout/main"


def main():
    source = MAIN_PY.read_bytes()

    match = re.search(r'^VERSION = "([^"]+)"', source.decode("utf-8"), re.MULTILINE)
    if not match:
        sys.exit("main.py에서 VERSION을 찾지 못했습니다.")
    version = match.group(1)

    # 학생 PC가 적용 전에 하는 검사를 여기서 먼저 돌려, 깨진 버전이 나가지 않게 한다
    try:
        compile(source, "main.py", "exec")
    except SyntaxError as e:
        sys.exit(f"main.py에 문법 오류가 있습니다: {e}")

    result = subprocess.run(
        [sys.executable, str(MAIN_PY), "--selftest"], capture_output=True, timeout=60
    )
    if result.returncode != 0:
        sys.exit(f"selftest 실패, 배포를 중단합니다:\n{result.stderr.decode('utf-8', 'replace')}")

    manifest = {
        "version": version,
        "url": f"{RAW_BASE}/main.py",
        "sha256": hashlib.sha256(source).hexdigest(),
        "enabled": True,
    }
    VERSION_JSON.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"version.json 생성 완료 (v{version}, sha256 {manifest['sha256'][:12]}...)")
    print("main.py와 version.json을 함께 커밋해야 합니다.")


if __name__ == "__main__":
    main()
