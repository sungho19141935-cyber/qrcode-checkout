// POST /api/status — 관리자가 설치 현황(어느 PC가 언제 마지막으로 살아있었는지)을 조회.
// 학생 PC 이름이 담기므로 비밀번호 확인을 거친다.
const { verifyPassword } = require("./_auth");

const STATUS_FILENAME = "admin_status.json";

module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    res.status(405).json({ error: "POST만 허용됩니다." });
    return;
  }

  const { password } = req.body || {};
  let ok;
  try {
    ok = password ? await verifyPassword(password) : false;
  } catch (e) {
    res.status(500).json({ error: String(e.message || e) });
    return;
  }
  if (!ok) {
    res.status(401).json({ error: "비밀번호가 올바르지 않습니다." });
    return;
  }

  const gistId = process.env.AUTH_GIST_ID;
  const token = process.env.GITHUB_TOKEN;
  if (!gistId || !token) {
    res.status(500).json({ error: "서버에 AUTH_GIST_ID/GITHUB_TOKEN이 설정되지 않았습니다." });
    return;
  }

  try {
    const r = await fetch(`https://api.github.com/gists/${gistId}`, {
      headers: { Authorization: `token ${token}`, Accept: "application/vnd.github+json" },
    });
    if (!r.ok) throw new Error(`조회 실패 (${r.status})`);
    const data = await r.json();
    const file = data.files && data.files[STATUS_FILENAME];
    if (!file) {
      res.status(200).json({ records: {} });
      return;
    }

    let content = file.content;
    if (file.truncated) {
      const raw = await fetch(file.raw_url, { headers: { Authorization: `token ${token}` } });
      if (!raw.ok) throw new Error("원본 조회 실패");
      content = await raw.text();
    }

    let records = {};
    try {
      records = JSON.parse(content || "{}");
    } catch {
      records = {};
    }
    res.status(200).json({ records });
  } catch (e) {
    res.status(502).json({ error: String(e.message || e) });
  }
};
