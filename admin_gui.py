"""관리자 전용: 중앙(GitHub Gist) QR 설정을 GUI로 갱신하는 도구.

이 파일과 admin_config.json은 학생들에게 배포하지 마세요.
admin_update.py의 핵심 로직(비밀번호 해시, Gist 조회/갱신)을 그대로 재사용합니다.
"""

import tkinter as tk
import urllib.error
from tkinter import messagebox, ttk

import admin_update as core


class AdminApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("퇴실 QR 관리자 도구")
        self.geometry("480x420")
        self.resizable(False, False)

        self.admin_config = core.load_admin_config()
        self.unlocked = False

        self.lock_frame = ttk.Frame(self, padding=20)
        self.main_frame = ttk.Frame(self, padding=20)

        self._build_lock_frame()
        self._build_main_frame()

        self.lock_frame.pack(fill="both", expand=True)

    # ---------- 잠금 화면 ----------
    def _build_lock_frame(self):
        first_time = "password_hash" not in self.admin_config

        if first_time:
            ttk.Label(
                self.lock_frame,
                text="최초 실행입니다. 관리자 비밀번호를 설정하세요. (6자 이상)",
                wraplength=420,
            ).pack(pady=(0, 10))

            ttk.Label(self.lock_frame, text="새 비밀번호").pack(anchor="w")
            self.pw1_var = tk.StringVar()
            ttk.Entry(self.lock_frame, textvariable=self.pw1_var, show="*").pack(fill="x")

            ttk.Label(self.lock_frame, text="새 비밀번호 확인").pack(anchor="w", pady=(10, 0))
            self.pw2_var = tk.StringVar()
            ttk.Entry(self.lock_frame, textvariable=self.pw2_var, show="*").pack(fill="x")

            ttk.Button(self.lock_frame, text="설정", command=self._set_password).pack(pady=20)
        else:
            ttk.Label(self.lock_frame, text="관리자 비밀번호").pack(anchor="w")
            self.pw_var = tk.StringVar()
            entry = ttk.Entry(self.lock_frame, textvariable=self.pw_var, show="*")
            entry.pack(fill="x")
            entry.bind("<Return>", lambda _e: self._unlock())
            entry.focus_set()

            ttk.Button(self.lock_frame, text="잠금 해제", command=self._unlock).pack(pady=20)

    def _set_password(self):
        pw1, pw2 = self.pw1_var.get(), self.pw2_var.get()
        if pw1 != pw2:
            messagebox.showerror("오류", "비밀번호가 일치하지 않습니다.")
            return
        if len(pw1) < 6:
            messagebox.showerror("오류", "비밀번호는 6자 이상이어야 합니다.")
            return

        import secrets
        import binascii

        salt = secrets.token_bytes(16)
        self.admin_config["salt"] = binascii.hexlify(salt).decode("ascii")
        self.admin_config["password_hash"] = core.hash_password(pw1, salt)
        core.save_admin_config(self.admin_config)

        messagebox.showinfo("완료", "비밀번호가 설정되었습니다. 다시 실행해 로그인하세요.")
        self.destroy()

    def _unlock(self):
        import binascii

        salt = binascii.unhexlify(self.admin_config["salt"])
        if core.hash_password(self.pw_var.get(), salt) != self.admin_config["password_hash"]:
            messagebox.showerror("오류", "비밀번호가 올바르지 않습니다.")
            return

        self.unlocked = True
        self.lock_frame.pack_forget()
        self.main_frame.pack(fill="both", expand=True)
        self._load_saved_fields()

    # ---------- 메인 화면 ----------
    def _build_main_frame(self):
        f = self.main_frame

        ttk.Label(f, text="Gist ID").pack(anchor="w")
        self.gist_id_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.gist_id_var).pack(fill="x")

        ttk.Label(f, text="Gist 파일 이름").pack(anchor="w", pady=(10, 0))
        self.gist_filename_var = tk.StringVar(value="bootcamp_qr_config.json")
        ttk.Entry(f, textvariable=self.gist_filename_var).pack(fill="x")

        ttk.Label(f, text="GitHub Personal Access Token (gist 권한)").pack(anchor="w", pady=(10, 0))
        self.token_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.token_var, show="*").pack(fill="x")

        self.save_token_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            f, text="이 컴퓨터에 토큰 저장 (다음부터 비밀번호만 입력)", variable=self.save_token_var
        ).pack(anchor="w", pady=(4, 0))

        ttk.Separator(f).pack(fill="x", pady=15)

        ttk.Label(f, text="퇴실 QR URL").pack(anchor="w")
        self.url_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.url_var).pack(fill="x")

        ttk.Label(f, text="퇴실 시각 (HH:MM)").pack(anchor="w", pady=(10, 0))
        self.time_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.time_var).pack(fill="x")

        btn_row = ttk.Frame(f)
        btn_row.pack(fill="x", pady=20)
        ttk.Button(btn_row, text="현재 값 불러오기", command=self._load_current).pack(
            side="left", expand=True, fill="x", padx=(0, 5)
        )
        ttk.Button(btn_row, text="Gist에 반영", command=self._save_to_gist).pack(
            side="left", expand=True, fill="x", padx=(5, 0)
        )

        self.status_var = tk.StringVar(value="")
        ttk.Label(f, textvariable=self.status_var, foreground="gray", wraplength=420).pack(
            anchor="w"
        )

    def _load_saved_fields(self):
        self.gist_id_var.set(self.admin_config.get("gist_id", ""))
        self.gist_filename_var.set(
            self.admin_config.get("gist_filename", "bootcamp_qr_config.json")
        )
        self.token_var.set(self.admin_config.get("github_token", ""))

    def _persist_connection_fields(self):
        self.admin_config["gist_id"] = self.gist_id_var.get().strip()
        self.admin_config["gist_filename"] = self.gist_filename_var.get().strip()
        if self.save_token_var.get():
            self.admin_config["github_token"] = self.token_var.get().strip()
        core.save_admin_config(self.admin_config)

    def _load_current(self):
        gist_id = self.gist_id_var.get().strip()
        filename = self.gist_filename_var.get().strip()
        token = self.token_var.get().strip()
        if not (gist_id and filename and token):
            messagebox.showerror("오류", "Gist ID / 파일 이름 / 토큰을 모두 입력하세요.")
            return

        try:
            current = core.fetch_gist_file(gist_id, filename, token)
        except urllib.error.URLError as e:
            messagebox.showerror("조회 실패", str(e))
            return

        self.url_var.set(current.get("checkout_url", ""))
        self.time_var.set(current.get("checkout_time", "18:00"))
        self._persist_connection_fields()
        self.status_var.set("현재 Gist 값을 불러왔습니다.")

    def _save_to_gist(self):
        gist_id = self.gist_id_var.get().strip()
        filename = self.gist_filename_var.get().strip()
        token = self.token_var.get().strip()
        url = self.url_var.get().strip()
        time_str = self.time_var.get().strip()

        if not (gist_id and filename and token and url and time_str):
            messagebox.showerror("오류", "모든 항목을 입력하세요.")
            return

        try:
            raw_url = core.update_gist_file(
                gist_id, filename, token, {"checkout_url": url, "checkout_time": time_str}
            )
        except urllib.error.URLError as e:
            messagebox.showerror("갱신 실패", str(e))
            return

        self._persist_connection_fields()
        self.status_var.set(f"갱신 완료. 학생 PC는 다음 동기화 주기에 자동 반영됩니다.\n{raw_url}")
        messagebox.showinfo("완료", "QR 설정이 Gist에 반영되었습니다.")


if __name__ == "__main__":
    AdminApp().mainloop()
