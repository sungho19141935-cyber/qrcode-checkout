import argparse
import base64
import binascii
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import tkinter as tk
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Optional

import qrcode
from PIL import Image, ImageTk

CONFIG_PATH = Path(__file__).parent / "config.json"
CACHE_PATH = Path(__file__).parent / "cache.json"
LOG_PATH = Path(__file__).parent / "qrcode.log"
LOG_MAX_BYTES = 512_000
BACKUP_PATH = Path(__file__).parent / "main.py.bak"

VERSION = "1.1.2"
DEFAULT_UPDATE_URL = (
    "https://raw.githubusercontent.com/sungho19141935-cyber/qrcode-checkout/main/version.json"
)
DEFAULT_UPDATE_INTERVAL = 3600  # 1시간마다 확인
MIN_MAIN_PY_BYTES = 5_000  # 이보다 작으면 잘린 응답으로 간주

DEFAULT_CHECKOUT_TIME = "18:00"
DEFAULT_ACTIVE_DAYS = ["mon", "tue", "wed", "thu", "fri"]
DEFAULT_CATCHUP_MINUTES = 120  # 절전/부팅 지연으로 정시를 놓쳤을 때 뒤늦게라도 띄우는 허용 범위
WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]  # datetime.weekday() 순서


def log(message: str):
    """화면과 로그 파일에 함께 기록한다.

    pythonw.exe로 실행하면 콘솔이 없어 print 출력이 전부 사라진다. QR이 안 떴을 때
    동기화 실패인지, 애초에 실행이 안 된 것인지 구분하려면 파일 기록이 필요하다.
    """
    print(message)
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {message}"
    try:
        if LOG_PATH.exists() and LOG_PATH.stat().st_size > LOG_MAX_BYTES:
            # 오래된 절반을 버리고 최근 기록만 남긴다 (파일 무한 증가 방지)
            tail = LOG_PATH.read_text(encoding="utf-8", errors="replace")[-LOG_MAX_BYTES // 2 :]
            LOG_PATH.write_text(tail, encoding="utf-8")
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass  # 로그를 못 남겨도 프로그램은 계속 돌아야 한다


def load_config():
    # 편집기나 스크립트가 BOM을 붙여 저장해도 읽히도록 utf-8-sig로 연다
    with open(CONFIG_PATH, encoding="utf-8-sig") as f:
        return json.load(f)


def load_cache():
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, encoding="utf-8-sig") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_cache(data: dict):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_remote_config(sync_url: str, timeout: int = 10) -> Optional[dict]:
    """관리자가 갱신하는 중앙 설정(Gist 등)을 가져온다. 실패하면 None."""
    try:
        # raw.githubusercontent.com은 CDN에서 몇 분간 응답을 캐시하므로,
        # 캐시 버스팅 쿼리를 붙여 항상 최신 내용을 받아온다.
        sep = "&" if "?" in sync_url else "?"
        busted_url = f"{sync_url}{sep}t={int(time.time())}"
        req = urllib.request.Request(busted_url, headers={"Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if "checkout_time" not in data or not ("qr_image" in data or "checkout_url" in data):
            log("[QRcode] 원격 설정에 checkout_time과 qr_image(또는 checkout_url)가 필요합니다. 무시합니다.")
            return None
        return data
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
        log(f"[QRcode] 원격 설정 갱신 실패 (마지막 캐시 사용): {e}")
        return None


def make_qr_image(url: str, box_size: int = 10):
    qr = qrcode.QRCode(box_size=box_size, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def decode_qr_image(qr_image_b64: str):
    """관리자가 업로드한 QR 이미지(base64)를 디코딩한다. 'data:image/png;base64,' 접두사도 허용."""
    b64 = qr_image_b64.split(",", 1)[-1] if "," in qr_image_b64 else qr_image_b64
    raw = base64.b64decode(b64)
    return Image.open(io.BytesIO(raw)).convert("RGB")


def get_display_image(state: dict):
    """관리자가 업로드한 QR 이미지가 있으면 그대로, 없으면 checkout_url로 QR을 생성해서 반환."""
    qr_image_b64 = state.get("qr_image")
    if qr_image_b64:
        try:
            return decode_qr_image(qr_image_b64)
        except (ValueError, binascii.Error, OSError) as e:
            log(f"[QRcode] 저장된 QR 이미지를 열지 못했습니다: {e}")
    return make_qr_image(state.get("checkout_url", ""))


def show_qr_window(state: dict, title: str, display_seconds: int):
    img = get_display_image(state)
    img.thumbnail((700, 700))

    root = tk.Tk()
    root.title(title)
    root.attributes("-topmost", True)
    root.attributes("-fullscreen", True)
    root.configure(bg="white")

    photo = ImageTk.PhotoImage(img)

    label_title = tk.Label(root, text=title, font=("Malgun Gothic", 24, "bold"), bg="white")
    label_title.pack(pady=(40, 10))

    label_img = tk.Label(root, image=photo, bg="white")
    label_img.pack(expand=True)

    label_hint = tk.Label(
        root,
        text="QR 스캔 후 아무 키나 누르거나 화면을 클릭하면 닫힙니다.",
        font=("Malgun Gothic", 14),
        bg="white",
        fg="gray",
    )
    label_hint.pack(pady=(10, 40))

    def close(_event=None):
        root.destroy()

    def close_by_click(_event=None):
        root.destroy()
        after_close_url = state.get("after_close_url")
        if after_close_url:
            webbrowser.open(after_close_url)

    root.bind("<Key>", close)
    root.bind("<Button-1>", close_by_click)
    root.after(display_seconds * 1000, close)

    root.mainloop()


def parse_hhmm(value: str) -> Optional[int]:
    """HH:MM 문자열을 자정 기준 분으로 변환. 형식이 틀리면 None."""
    try:
        hh, mm = value.split(":")
        minutes = int(hh) * 60 + int(mm)
    except (AttributeError, ValueError):
        return None
    return minutes if 0 <= minutes < 24 * 60 else None


def should_trigger(now: datetime, checkout_time: str, catchup_minutes: int) -> bool:
    """정시에 정확히 일치할 때만이 아니라, 정시를 지난 뒤 catchup_minutes 안이면 True.

    15초 간격 폴링이라도 노트북이 절전에 들어가거나 부팅이 늦으면 해당 1분을
    통째로 건너뛰어 그날 QR이 아예 뜨지 않는다. 지난 시각도 따라잡도록 한다.
    """
    target = parse_hhmm(checkout_time)
    if target is None:
        return False
    current = now.hour * 60 + now.minute
    return 0 <= current - target <= catchup_minutes


def fetch_json(url: str, timeout: int = 10):
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(
        f"{url}{sep}t={int(time.time())}", headers={"Cache-Control": "no-cache"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def verify_new_source(source: bytes, expected_sha256: str) -> Optional[str]:
    """새 main.py를 적용해도 되는지 검사한다. 문제가 있으면 사유 문자열, 없으면 None."""
    if len(source) < MIN_MAIN_PY_BYTES:
        return f"파일이 너무 작습니다 ({len(source)} bytes) - 응답이 잘린 것으로 보입니다"

    actual = hashlib.sha256(source).hexdigest()
    if actual != expected_sha256:
        return f"체크섬 불일치 (기대 {expected_sha256[:12]}..., 실제 {actual[:12]}...)"

    try:
        compile(source, "main.py", "exec")
    except SyntaxError as e:
        return f"문법 오류: {e}"

    if b"def run_scheduler" not in source:
        return "run_scheduler가 없습니다 - 올바른 프로그램 파일이 아닙니다"

    return None


def smoke_test(source: bytes) -> Optional[str]:
    """새 코드를 실제로 한 번 실행해본다. 정상 종료하지 못하면 사유를 돌려준다.

    문법만 통과하고 실행 즉시 죽는 버전으로 교체해버리면 학생 PC에서 프로그램이
    조용히 사라진다. 교체 전에 --selftest로 한 번 띄워보고 통과한 것만 적용한다.
    """
    tmp_dir = tempfile.mkdtemp(prefix="qrcode_update_")
    tmp_main = Path(tmp_dir) / "main.py"
    try:
        tmp_main.write_bytes(source)
        # 설정 파일도 같이 둬야 새 코드가 config를 읽을 수 있다
        try:
            tmp_main.with_name("config.json").write_text(
                CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8"
            )
        except OSError:
            pass

        result = subprocess.run(
            [sys.executable, str(tmp_main), "--selftest"],
            capture_output=True,
            timeout=60,
            cwd=tmp_dir,
        )
        if result.returncode != 0:
            detail = (result.stderr or b"").decode("utf-8", "replace").strip()[-300:]
            return f"실행 검증 실패 (종료코드 {result.returncode}) {detail}"
        return None
    except (subprocess.TimeoutExpired, OSError) as e:
        return f"실행 검증 중 오류: {e}"
    finally:
        try:
            for f in Path(tmp_dir).iterdir():
                f.unlink(missing_ok=True)
            Path(tmp_dir).rmdir()
        except OSError:
            pass


def apply_update(source: bytes) -> bool:
    """main.py를 교체한다. 직전 버전은 main.py.bak으로 남긴다."""
    me = Path(__file__).resolve()
    tmp = me.with_suffix(".py.new")
    try:
        tmp.write_bytes(source)
        try:
            BACKUP_PATH.write_bytes(me.read_bytes())
        except OSError as e:
            log(f"[QRcode] 백업 실패, 업데이트를 중단합니다: {e}")
            tmp.unlink(missing_ok=True)
            return False
        os.replace(tmp, me)  # 같은 볼륨 내 원자적 교체
        return True
    except OSError as e:
        log(f"[QRcode] 업데이트 적용 실패: {e}")
        tmp.unlink(missing_ok=True)
        return False


def restart_self():
    """교체된 코드로 새 프로세스를 띄우고 현재 프로세스는 종료한다."""
    me = str(Path(__file__).resolve())
    flags = 0x00000008 if os.name == "nt" else 0  # DETACHED_PROCESS
    subprocess.Popen(
        [sys.executable, me], cwd=str(Path(me).parent), creationflags=flags, close_fds=True
    )
    sys.exit(0)


def check_for_update(update_url: str) -> bool:
    """새 버전이 있으면 검증 후 교체한다. 교체했으면 True (호출자가 재시작)."""
    try:
        manifest = fetch_json(update_url)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError) as e:
        log(f"[QRcode] 업데이트 확인 실패 (무시하고 계속): {e}")
        return False

    if manifest.get("enabled") is False:
        return False  # 긴급 중단 스위치

    remote_version = str(manifest.get("version", ""))
    if not remote_version or remote_version == VERSION:
        return False

    source_url = manifest.get("url")
    expected_sha = str(manifest.get("sha256", ""))
    if not source_url or not expected_sha:
        log("[QRcode] 업데이트 정보에 url/sha256이 없어 건너뜁니다.")
        return False

    log(f"[QRcode] 새 버전 발견: {VERSION} -> {remote_version}, 내려받는 중...")
    try:
        sep = "&" if "?" in source_url else "?"
        req = urllib.request.Request(
            f"{source_url}{sep}t={int(time.time())}", headers={"Cache-Control": "no-cache"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            source = resp.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        log(f"[QRcode] 새 버전 내려받기 실패: {e}")
        return False

    problem = verify_new_source(source, expected_sha)
    if problem:
        log(f"[QRcode] 업데이트 거부 - {problem}")
        return False

    problem = smoke_test(source)
    if problem:
        log(f"[QRcode] 업데이트 거부 - {problem}")
        return False

    # 디스크의 main.py가 이미 새 버전인 경우(다른 인스턴스가 먼저 교체했거나, 재시작에
    # 실패해 구버전이 메모리에 남아있는 경우)에는 다시 쓰지 않는다. 그대로 덮어쓰면
    # 멀쩡한 이전 버전 백업이 같은 내용으로 지워진다.
    try:
        if Path(__file__).resolve().read_bytes().replace(b"\r\n", b"\n") == source:
            log(f"[QRcode] 파일은 이미 v{remote_version}입니다. 재시작만 합니다.")
            return True
    except OSError:
        pass

    if not apply_update(source):
        return False

    log(f"[QRcode] 업데이트 완료: {VERSION} -> {remote_version}. 재시작합니다.")
    return True


def run_scheduler(config):
    sync_url = config.get("sync_url")
    fetch_interval = int(config.get("fetch_interval_seconds", 300))
    display_seconds = int(config.get("display_seconds", 600))
    window_title = config.get("window_title", "퇴실 QR코드")
    catchup_minutes = int(config.get("catchup_minutes", DEFAULT_CATCHUP_MINUTES))
    update_url = config.get("update_url", DEFAULT_UPDATE_URL)
    update_interval = int(config.get("update_check_seconds", DEFAULT_UPDATE_INTERVAL))

    state = load_cache()
    state.setdefault("checkout_url", config.get("checkout_url", ""))
    state.setdefault("qr_image", config.get("qr_image"))
    state.setdefault("checkout_time", config.get("checkout_time", DEFAULT_CHECKOUT_TIME))
    state.setdefault("active_days", config.get("active_days", DEFAULT_ACTIVE_DAYS))
    state.setdefault("after_close_url", config.get("after_close_url"))

    last_triggered_date = None
    last_fetch = 0.0
    last_update_check = 0.0
    synced_once = False

    log(
        f"[QRcode] 시작 v{VERSION} - 예정 시각 {state['checkout_time']}, "
        f"요일 {state.get('active_days')}, 따라잡기 {catchup_minutes}분"
    )
    if sync_url:
        log(f"[QRcode] 중앙 설정 동기화 사용: {sync_url} ({fetch_interval}초마다 갱신)")

    while True:
        now_ts = time.time()

        # QR을 띄우는 중에 교체가 끼어들지 않도록, 표시 직전이 아닐 때만 확인한다
        if update_url and now_ts - last_update_check >= update_interval:
            last_update_check = now_ts
            if check_for_update(update_url):
                restart_self()

        if sync_url and now_ts - last_fetch >= fetch_interval:
            last_fetch = now_ts
            remote = fetch_remote_config(sync_url)
            if remote:
                if not synced_once:
                    synced_once = True
                    log(f"[QRcode] 중앙 설정 첫 동기화 성공 (시각 {remote.get('checkout_time')})")
                if remote.get("checkout_time") != state.get("checkout_time") or remote.get(
                    "qr_image"
                ) != state.get("qr_image") or remote.get("checkout_url") != state.get(
                    "checkout_url"
                ) or remote.get("active_days") != state.get(
                    "active_days"
                ) or remote.get("after_close_url") != state.get("after_close_url"):
                    log(
                        f"[QRcode] 설정 갱신됨 -> 시각: {remote.get('checkout_time')}, "
                        f"요일: {remote.get('active_days', state['active_days'])}"
                    )
                state["checkout_url"] = remote.get("checkout_url", state.get("checkout_url", ""))
                state["qr_image"] = remote.get("qr_image", state.get("qr_image"))
                state["checkout_time"] = remote.get("checkout_time", state["checkout_time"])
                state["active_days"] = remote.get("active_days", state["active_days"])
                state["after_close_url"] = remote.get("after_close_url", state.get("after_close_url"))
                save_cache(state)

        now = datetime.now()
        now_hm = now.strftime("%H:%M")
        today = now.strftime("%Y-%m-%d")

        today_key = WEEKDAY_KEYS[now.weekday()]
        is_active_day = today_key in state.get("active_days", DEFAULT_ACTIVE_DAYS)
        if (
            last_triggered_date != today
            and is_active_day
            and should_trigger(now, state["checkout_time"], catchup_minutes)
        ):
            last_triggered_date = today
            log(f"[QRcode] {now_hm} (설정 {state['checkout_time']}) - QR 화면 표시")
            show_qr_window(state, window_title, display_seconds)

        time.sleep(15)


def main():
    parser = argparse.ArgumentParser(description="퇴실 QR코드 자동 표시 프로그램")
    parser.add_argument("--test-now", action="store_true", help="스케줄 무시하고 즉시 QR 표시")
    parser.add_argument("--version", action="store_true", help="버전 출력 후 종료")
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="네트워크/화면 없이 기본 동작만 점검하고 종료 (자동 업데이트 검증용)",
    )
    args = parser.parse_args()

    if args.version:
        print(VERSION)
        return

    if args.selftest:
        # 자동 업데이트가 이 코드를 적용해도 되는지 판단하는 기준이다.
        # 네트워크도 화면도 쓰지 않고, 핵심 경로만 실제로 한 번씩 실행해본다.
        config = load_config()
        assert parse_hhmm("18:00") == 1080, "parse_hhmm 오류"
        assert parse_hhmm("이상한값") is None, "parse_hhmm 예외 처리 오류"
        assert should_trigger(datetime(2026, 1, 1, 18, 0), "18:00", 0), "정시 트리거 오류"
        assert should_trigger(datetime(2026, 1, 1, 18, 30), "18:00", 120), "따라잡기 오류"
        assert not should_trigger(datetime(2026, 1, 1, 17, 59), "18:00", 120), "이른 트리거 오류"
        make_qr_image("https://example.com/selftest")  # 이미지 생성 경로
        int(config.get("display_seconds", 600))
        print(f"selftest OK (v{VERSION})")
        return

    config = load_config()

    if args.test_now:
        state = load_cache()
        state.setdefault("checkout_url", config.get("checkout_url", ""))
        state.setdefault("qr_image", config.get("qr_image"))
        state.setdefault("after_close_url", config.get("after_close_url"))
        if config.get("sync_url"):
            remote = fetch_remote_config(config["sync_url"])
            if remote:
                state["checkout_url"] = remote.get("checkout_url", state.get("checkout_url", ""))
                state["qr_image"] = remote.get("qr_image", state.get("qr_image"))
                state["after_close_url"] = remote.get("after_close_url", state.get("after_close_url"))
        show_qr_window(
            state,
            config.get("window_title", "퇴실 QR코드"),
            int(config.get("display_seconds", 600)),
        )
        return

    try:
        run_scheduler(config)
    except KeyboardInterrupt:
        log("[QRcode] 종료합니다.")
        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException:
        # pythonw.exe에는 콘솔이 없어, 여기서 기록하지 않으면 프로그램이 왜 사라졌는지
        # 알 방법이 전혀 없다.
        import traceback

        log("[QRcode] 치명적 오류로 종료됩니다:\n" + traceback.format_exc())
        raise
