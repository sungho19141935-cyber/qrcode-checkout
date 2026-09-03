// POST /api/update — 비밀번호 인증 후 Gist의 checkout_url/checkout_time을 갱신
const crypto = require("crypto");

function safeEqual(a, b) {
  const bufA = Buffer.from(String(a));
  const bufB = Buffer.from(String(b));
  if (bufA.length !== bufB.length) return false;
  return crypto.timingSafeEqual(bufA, bufB);
}

module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    res.status(405).json({ error: "POST만 허용됩니다." });
    return;
  }

  const { password, checkout_url, checkout_time } = req.body || {};

  const adminPassword = process.env.ADMIN_PASSWORD;
  if (!adminPassword) {
    res.status(500).json({ error: "서버에 ADMIN_PASSWORD가 설정되지 않았습니다." });
    return;
  }
  if (!password || !safeEqual(password, adminPassword)) {
    res.status(401).json({ error: "비밀번호가 올바르지 않습니다." });
    return;
  }

  if (!checkout_url || !checkout_time) {
    res.status(400).json({ error: "checkout_url과 checkout_time을 모두 입력하세요." });
    return;
  }
  if (!/^\d{2}:\d{2}$/.test(checkout_time)) {
    res.status(400).json({ error: "checkout_time은 HH:MM 형식이어야 합니다." });
    return;
  }

  const gistId = process.env.GIST_ID;
  const filename = process.env.GIST_FILENAME;
  const token = process.env.GITHUB_TOKEN;
  if (!gistId || !filename || !token) {
    res.status(500).json({ error: "서버에 GIST_ID/GIST_FILENAME/GITHUB_TOKEN이 설정되지 않았습니다." });
    return;
  }

  const content = JSON.stringify({ checkout_url, checkout_time }, null, 2);

  try {
    const r = await fetch(`https://api.github.com/gists/${gistId}`, {
      method: "PATCH",
      headers: {
        Authorization: `token ${token}`,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ files: { [filename]: { content } } }),
    });

    if (!r.ok) {
      const detail = await r.text();
      res.status(502).json({ error: "Gist 업데이트 실패", detail });
      return;
    }

    const result = await r.json();
    res.status(200).json({ ok: true, raw_url: result.files[filename].raw_url });
  } catch (e) {
    res.status(502).json({ error: "Gist 업데이트 중 오류", detail: String(e) });
  }
};
