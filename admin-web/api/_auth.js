// 관리자 비밀번호 검증/변경 공용 로직.
// 비밀번호 해시는 별도의 "secret gist"(AUTH_GIST_ID)에 저장한다 — 학생 프로그램이
// 읽는 공개 Gist(GIST_ID)와는 완전히 분리되어 있어 유출 위험이 없다.
// AUTH_GIST_ID가 아직 설정되지 않았거나 해시가 비어있으면 ADMIN_PASSWORD 환경변수로
// 대체 동작한다 (마이그레이션 전 하위 호환).
const crypto = require("crypto");

const AUTH_FILENAME = "admin_auth.json";

function safeEqual(a, b) {
  const bufA = Buffer.from(String(a));
  const bufB = Buffer.from(String(b));
  if (bufA.length !== bufB.length) return false;
  return crypto.timingSafeEqual(bufA, bufB);
}

function hashPassword(password, salt) {
  return crypto.scryptSync(String(password), salt, 64).toString("hex");
}

async function fetchAuthGist() {
  const authGistId = process.env.AUTH_GIST_ID;
  const token = process.env.GITHUB_TOKEN;
  if (!authGistId || !token) return null;

  const r = await fetch(`https://api.github.com/gists/${authGistId}`, {
    headers: {
      Authorization: `token ${token}`,
      Accept: "application/vnd.github+json",
    },
  });
  if (!r.ok) return null;

  const data = await r.json();
  const file = data.files && data.files[AUTH_FILENAME];
  if (!file || !file.content) return null;
  try {
    return JSON.parse(file.content);
  } catch {
    return null;
  }
}

// 비밀번호가 맞는지 확인한다. 서버에 비밀번호 자체가 설정되지 않았으면 예외를 던진다.
async function verifyPassword(password) {
  const auth = await fetchAuthGist();
  if (auth && auth.password_hash && auth.salt) {
    const computed = hashPassword(password, auth.salt);
    return safeEqual(computed, auth.password_hash);
  }

  const fallback = process.env.ADMIN_PASSWORD;
  if (!fallback) {
    throw new Error("서버에 비밀번호가 설정되지 않았습니다.");
  }
  return safeEqual(password, fallback);
}

// 새 비밀번호를 secret gist에 저장한다. AUTH_GIST_ID가 없으면 예외를 던진다.
async function saveNewPassword(newPassword) {
  const authGistId = process.env.AUTH_GIST_ID;
  const token = process.env.GITHUB_TOKEN;
  if (!authGistId || !token) {
    throw new Error(
      "AUTH_GIST_ID가 설정되지 않아 비밀번호를 저장할 수 없습니다. admin-web/README.md의 안내를 먼저 따라주세요."
    );
  }

  const salt = crypto.randomBytes(16).toString("hex");
  const hash = hashPassword(newPassword, salt);
  const content = JSON.stringify({ password_hash: hash, salt }, null, 2);

  const r = await fetch(`https://api.github.com/gists/${authGistId}`, {
    method: "PATCH",
    headers: {
      Authorization: `token ${token}`,
      Accept: "application/vnd.github+json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ files: { [AUTH_FILENAME]: { content } } }),
  });

  if (!r.ok) {
    const detail = await r.text();
    throw new Error(`비밀번호 저장 실패: ${detail}`);
  }
}

module.exports = { verifyPassword, saveNewPassword };
