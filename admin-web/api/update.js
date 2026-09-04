// POST /api/update — 비밀번호 인증 후 Gist의 checkout_url/checkout_time을 갱신
const crypto = require("crypto");

const VALID_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

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

  const { password, checkout_time, qr_image, active_days } = req.body || {};

  const adminPassword = process.env.ADMIN_PASSWORD;
  if (!adminPassword) {
    res.status(500).json({ error: "서버에 ADMIN_PASSWORD가 설정되지 않았습니다." });
    return;
  }
  if (!password || !safeEqual(password, adminPassword)) {
    res.status(401).json({ error: "비밀번호가 올바르지 않습니다." });
    return;
  }

  if (!checkout_time || !qr_image) {
    res.status(400).json({ error: "QR 이미지와 checkout_time을 모두 입력하세요." });
    return;
  }
  if (!/^\d{2}:\d{2}$/.test(checkout_time)) {
    res.status(400).json({ error: "checkout_time은 HH:MM 형식이어야 합니다." });
    return;
  }
  if (!/^data:image\/(png|jpeg|jpg|webp);base64,/.test(qr_image)) {
    res.status(400).json({ error: "qr_image는 data:image/...;base64, 형식의 이미지여야 합니다." });
    return;
  }
  // Vercel Serverless Function 요청 본문 한도(4.5MB)를 넘지 않도록 여유를 두고 제한
  if (qr_image.length > 3_500_000) {
    res.status(400).json({ error: "이미지가 너무 큽니다. 더 작은 이미지(스크린샷 크롭 등)를 사용하세요." });
    return;
  }

  let days = VALID_DAYS.slice(0, 5); // 기본값: 월~금
  if (active_days !== undefined) {
    if (!Array.isArray(active_days) || active_days.length === 0 || !active_days.every((d) => VALID_DAYS.includes(d))) {
      res.status(400).json({ error: "active_days는 mon~sun 중 하나 이상을 담은 배열이어야 합니다." });
      return;
    }
    days = active_days;
  }

  const gistId = process.env.GIST_ID;
  const filename = process.env.GIST_FILENAME;
  const token = process.env.GITHUB_TOKEN;
  if (!gistId || !filename || !token) {
    res.status(500).json({ error: "서버에 GIST_ID/GIST_FILENAME/GITHUB_TOKEN이 설정되지 않았습니다." });
    return;
  }

  const content = JSON.stringify({ qr_image, checkout_time, active_days: days }, null, 2);

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
