"""관리자 전용: 중앙(GitHub Gist) QR 설정을 갱신하는 도구.

이 파일과 admin_config.json은 학생들에게 배포하지 마세요.
"""

import argparse
import binascii
import getpass
import hashlib
import json
import os
import secrets
import sys
import urllib.error
import urllib.request
from pathlib import Path

ADMIN_CONFIG_PATH = Path(__file__).parent / "admin_config.json"
PBKDF2_ITERATIONS = 200_000


def load_admin_config() -> dict:
    if ADMIN_CONFIG_PATH.exists():
        with open(ADMIN_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_admin_config(data: dict):
    with open(ADMIN_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    if os.name != "nt":
        os.chmod(ADMIN_CONFIG_PATH, 0o600)


def hash_password(password: str, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return binascii.hexlify(dk).decode("ascii")


def set_password(admin_config: dict):
    print("관리자 비밀번호를 설정합니다.")
    while True:
        pw1 = getpass.getpass("새 비밀번호: ")
        pw2 = getpass.getpass("새 비밀번호 확인: ")
        if pw1 != pw2:
            print("비밀번호가 일치하지 않습니다. 다시 입력하세요.\n")
            continue
        if len(pw1) < 6:
            print("비밀번호는 6자 이상으로 설정하세요.\n")
            continue
        break

    salt = secrets.token_bytes(16)
    admin_config["salt"] = binascii.hexlify(salt).decode("ascii")
    admin_config["password_hash"] = hash_password(pw1, salt)
    save_admin_config(admin_config)
    print("비밀번호가 저장되었습니다.\n")


def verify_password(admin_config: dict) -> bool:
    salt = binascii.unhexlify(admin_config["salt"])
    attempt = getpass.getpass("관리자 비밀번호: ")
    return hash_password(attempt, salt) == admin_config["password_hash"]


def get_github_token(admin_config: dict, save_token: bool) -> str:
    token = os.environ.get("GITHUB_TOKEN") or admin_config.get("github_token")
    if token:
        return token
    token = getpass.getpass("GitHub Personal Access Token (gist 권한 필요): ")
    if save_token:
        admin_config["github_token"] = token
        save_admin_config(admin_config)
        print("(토큰을 admin_config.json에 저장했습니다. 이 파일을 절대 공유하지 마세요.)")
    return token


def fetch_gist_file(gist_id: str, filename: str, token: str) -> dict:
    req = urllib.request.Request(
        f"https://api.github.com/gists/{gist_id}",
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        gist = json.loads(resp.read().decode("utf-8"))
    file_info = gist.get("files", {}).get(filename)
    if not file_info:
        return {}
    return json.loads(file_info["content"])


def update_gist_file(gist_id: str, filename: str, token: str, content: dict) -> str:
    body = json.dumps(
        {"files": {filename: {"content": json.dumps(content, ensure_ascii=False, indent=2)}}}
    ).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.github.com/gists/{gist_id}",
        data=body,
        method="PATCH",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["files"][filename]["raw_url"]


def main():
    parser = argparse.ArgumentParser(description="관리자용 중앙 QR 설정 갱신 도구")
    parser.add_argument("--set-password", action="store_true", help="관리자 비밀번호를 새로 설정")
    parser.add_argument("--save-token", action="store_true", help="GitHub 토큰을 로컬에 저장")
    parser.add_argument("--url", help="새 퇴실 QR URL (미입력 시 프롬프트로 입력)")
    parser.add_argument("--time", help="새 퇴실 시각 HH:MM (미입력 시 기존 값 유지)")
    args = parser.parse_args()

    admin_config = load_admin_config()

    if args.set_password or "password_hash" not in admin_config:
        if "password_hash" not in admin_config:
            print("최초 실행입니다. 관리자 비밀번호를 먼저 설정하세요.\n")
        set_password(admin_config)
        if args.set_password and not args.url:
            return

    if not verify_password(admin_config):
        print("비밀번호가 올바르지 않습니다.")
        sys.exit(1)

    gist_id = admin_config.get("gist_id") or input("Gist ID: ").strip()
    gist_filename = admin_config.get("gist_filename") or input(
        "Gist 파일 이름 (예: bootcamp_qr_config.json): "
    ).strip()
    admin_config["gist_id"] = gist_id
    admin_config["gist_filename"] = gist_filename
    save_admin_config(admin_config)

    token = get_github_token(admin_config, args.save_token)

    try:
        current = fetch_gist_file(gist_id, gist_filename, token)
    except urllib.error.URLError as e:
        print(f"Gist 조회 실패: {e}")
        sys.exit(1)

    new_url = args.url or input(
        f"새 퇴실 QR URL [{current.get('checkout_url', '없음')}]: "
    ).strip()
    if not new_url:
        new_url = current.get("checkout_url", "")

    new_time = args.time or input(
        f"새 퇴실 시각 HH:MM (엔터 시 유지: {current.get('checkout_time', '18:00')}): "
    ).strip()
    if not new_time:
        new_time = current.get("checkout_time", "18:00")

    updated = {"checkout_url": new_url, "checkout_time": new_time}

    try:
        raw_url = update_gist_file(gist_id, gist_filename, token, updated)
    except urllib.error.URLError as e:
        print(f"Gist 업데이트 실패: {e}")
        sys.exit(1)

    print("\n갱신 완료.")
    print(f"  checkout_url: {updated['checkout_url']}")
    print(f"  checkout_time: {updated['checkout_time']}")
    print(f"  raw URL: {raw_url}")
    print("모든 학생 PC는 다음 동기화 주기(fetch_interval_seconds)에 자동으로 반영됩니다.")


if __name__ == "__main__":
    main()
