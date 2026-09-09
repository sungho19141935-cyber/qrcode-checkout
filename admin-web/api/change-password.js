// POST /api/change-password — 현재 비밀번호 확인 후 새 비밀번호를 secret gist에 저장
const { verifyPassword, saveNewPassword } = require("./_auth");

module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    res.status(405).json({ error: "POST만 허용됩니다." });
    return;
  }

  const { current_password, new_password } = req.body || {};

  if (!current_password || !new_password) {
    res.status(400).json({ error: "현재 비밀번호와 새 비밀번호를 모두 입력하세요." });
    return;
  }
  if (String(new_password).length < 6) {
    res.status(400).json({ error: "새 비밀번호는 6자 이상이어야 합니다." });
    return;
  }

  let ok;
  try {
    ok = await verifyPassword(current_password);
  } catch (e) {
    res.status(500).json({ error: String(e.message || e) });
    return;
  }
  if (!ok) {
    res.status(401).json({ error: "현재 비밀번호가 올바르지 않습니다." });
    return;
  }

  try {
    await saveNewPassword(new_password);
    res.status(200).json({ ok: true });
  } catch (e) {
    res.status(502).json({ error: String(e.message || e) });
  }
};
