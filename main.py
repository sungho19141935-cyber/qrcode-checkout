import argparse
import json
import sys
import time
import tkinter as tk
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

import qrcode
from PIL import ImageTk

CONFIG_PATH = Path(__file__).parent / "config.json"
CACHE_PATH = Path(__file__).parent / "cache.json"

DEFAULT_CHECKOUT_TIME = "18:00"


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_cache():
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, encoding="utf-8") as f:
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
        req = urllib.request.Request(sync_url, headers={"Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if "checkout_url" not in data:
            print("[QRcode] 원격 설정에 checkout_url이 없습니다. 무시합니다.")
            return None
        return data
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
        print(f"[QRcode] 원격 설정 갱신 실패 (마지막 캐시 사용): {e}")
        return None


def make_qr_image(url: str, box_size: int = 10):
    qr = qrcode.QRCode(box_size=box_size, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def show_qr_window(url: str, title: str, display_seconds: int):
    img = make_qr_image(url)

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

    root.bind("<Key>", close)
    root.bind("<Button-1>", close)
    root.after(display_seconds * 1000, close)

    root.mainloop()


def run_scheduler(config):
    sync_url = config.get("sync_url")
    fetch_interval = int(config.get("fetch_interval_seconds", 300))
    display_seconds = int(config.get("display_seconds", 600))
    window_title = config.get("window_title", "퇴실 QR코드")

    state = load_cache()
    state.setdefault("checkout_url", config.get("checkout_url", ""))
    state.setdefault("checkout_time", config.get("checkout_time", DEFAULT_CHECKOUT_TIME))

    last_triggered_date = None
    last_fetch = 0.0

    print("[QRcode] 대기 중... (Ctrl+C 종료)")
    if sync_url:
        print(f"[QRcode] 중앙 설정 동기화 사용: {sync_url} ({fetch_interval}초마다 갱신)")

    while True:
        now_ts = time.time()

        if sync_url and now_ts - last_fetch >= fetch_interval:
            last_fetch = now_ts
            remote = fetch_remote_config(sync_url)
            if remote:
                if remote.get("checkout_url") != state.get("checkout_url") or remote.get(
                    "checkout_time"
                ) != state.get("checkout_time"):
                    print(
                        f"[QRcode] 설정 갱신됨 -> URL: {remote.get('checkout_url')}, "
                        f"시각: {remote.get('checkout_time')}"
                    )
                state["checkout_url"] = remote.get("checkout_url", state["checkout_url"])
                state["checkout_time"] = remote.get("checkout_time", state["checkout_time"])
                save_cache(state)

        now = datetime.now()
        now_hm = now.strftime("%H:%M")
        today = now.strftime("%Y-%m-%d")

        if now_hm == state["checkout_time"] and last_triggered_date != today:
            last_triggered_date = today
            print(f"[QRcode] {now_hm} 도달 - QR 화면 표시 ({state['checkout_url']})")
            show_qr_window(state["checkout_url"], window_title, display_seconds)

        time.sleep(15)


def main():
    parser = argparse.ArgumentParser(description="퇴실 QR코드 자동 표시 프로그램")
    parser.add_argument("--test-now", action="store_true", help="스케줄 무시하고 즉시 QR 표시")
    args = parser.parse_args()

    config = load_config()

    if args.test_now:
        state = load_cache()
        url = state.get("checkout_url") or config.get("checkout_url", "")
        if config.get("sync_url"):
            remote = fetch_remote_config(config["sync_url"])
            if remote:
                url = remote.get("checkout_url", url)
        show_qr_window(
            url,
            config.get("window_title", "퇴실 QR코드"),
            int(config.get("display_seconds", 600)),
        )
        return

    try:
        run_scheduler(config)
    except KeyboardInterrupt:
        print("\n[QRcode] 종료합니다.")
        sys.exit(0)


if __name__ == "__main__":
    main()
