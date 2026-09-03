// GET /api/current — 현재 Gist에 등록된 QR 설정을 반환 (인증 불필요, 읽기 전용)
module.exports = async function handler(req, res) {
  if (req.method !== "GET") {
    res.status(405).json({ error: "GET만 허용됩니다." });
    return;
  }

  const rawUrl = process.env.GIST_RAW_URL;
  if (!rawUrl) {
    res.status(500).json({ error: "서버에 GIST_RAW_URL이 설정되지 않았습니다." });
    return;
  }

  try {
    const r = await fetch(rawUrl, { cache: "no-store" });
    if (!r.ok) throw new Error(`gist fetch ${r.status}`);
    const data = await r.json();
    res.status(200).json(data);
  } catch (e) {
    res.status(502).json({ error: "현재 설정을 불러오지 못했습니다.", detail: String(e) });
  }
};
