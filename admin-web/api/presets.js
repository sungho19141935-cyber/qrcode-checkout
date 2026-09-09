// POST /api/presets — 관리자가 QR/시각/요일/링크 조합을 이름 붙여 저장/불러오기/삭제
// action: "list" | "save" | "rename" | "delete"
// 프리셋은 학생 프로그램이 읽는 GIST_FILENAME과는 다른 파일(admin_presets.json)에
// 같은 gist(GIST_ID) 안에 저장되므로, 학생 쪽 폴링 트래픽에는 영향이 없다.
const crypto = require("crypto");
const { verifyPassword } = require("./_auth");

const PRESETS_FILENAME = "admin_presets.json";

async function fetchPresets() {
  const gistId = process.env.GIST_ID;
  const token = process.env.GITHUB_TOKEN;
  const r = await fetch(`https://api.github.com/gists/${gistId}`, {
    headers: {
      Authorization: `token ${token}`,
      Accept: "application/vnd.github+json",
    },
  });
  if (!r.ok) throw new Error("프리셋 조회 실패");
  const data = await r.json();
  const file = data.files && data.files[PRESETS_FILENAME];
  if (!file) return {};

  // GitHub Gist API는 파일이 일정 크기를 넘으면 content를 잘라서 응답하고
  // truncated: true를 표시한다 (QR 이미지가 여러 개 쌓이면 흔히 발생). 이 경우
  // raw_url에서 잘리지 않은 전체 내용을 다시 받아와야 한다.
  let content = file.content;
  if (file.truncated) {
    const rawR = await fetch(file.raw_url, {
      headers: { Authorization: `token ${token}` },
    });
    if (!rawR.ok) throw new Error("프리셋 원본 조회 실패");
    content = await rawR.text();
  }
  if (!content) return {};

  try {
    return JSON.parse(content);
  } catch {
    return {};
  }
}

async function savePresets(presets) {
  const gistId = process.env.GIST_ID;
  const token = process.env.GITHUB_TOKEN;
  const content = JSON.stringify(presets, null, 2);
  const r = await fetch(`https://api.github.com/gists/${gistId}`, {
    method: "PATCH",
    headers: {
      Authorization: `token ${token}`,
      Accept: "application/vnd.github+json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ files: { [PRESETS_FILENAME]: { content } } }),
  });
  if (!r.ok) {
    const detail = await r.text();
    throw new Error(`프리셋 저장 실패: ${detail}`);
  }
}

module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    res.status(405).json({ error: "POST만 허용됩니다." });
    return;
  }

  const {
    password,
    action,
    id,
    name,
    checkout_time,
    qr_image,
    active_days,
    after_close_url,
  } = req.body || {};

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

  const gistId = process.env.GIST_ID;
  const token = process.env.GITHUB_TOKEN;
  if (!gistId || !token) {
    res.status(500).json({ error: "서버에 GIST_ID/GITHUB_TOKEN이 설정되지 않았습니다." });
    return;
  }

  try {
    const presets = await fetchPresets();

    if (action === "list") {
      res.status(200).json({ presets });
      return;
    }

    if (action === "save") {
      if (!name || !checkout_time || !qr_image) {
        res.status(400).json({ error: "설정 이름, 시각, QR 이미지는 필수입니다." });
        return;
      }
      // 프리셋이 쌓일수록 admin_presets.json 전체 용량이 커져 Gist API의 truncation
      // 한도를 넘기 쉬우므로, 이미지 한 장당 크기를 넉넉히 제한한다.
      if (qr_image.length > 1_000_000) {
        res.status(400).json({
          error: "이미지가 너무 큽니다. 프리셋에는 500KB 이하로 압축/크롭한 이미지를 사용하세요.",
        });
        return;
      }
      const presetId = id && presets[id] ? id : crypto.randomUUID();
      presets[presetId] = {
        name,
        checkout_time,
        qr_image,
        active_days: Array.isArray(active_days) && active_days.length
          ? active_days
          : ["mon", "tue", "wed", "thu", "fri"],
        after_close_url: after_close_url || "",
      };
      await savePresets(presets);
      res.status(200).json({ ok: true, id: presetId });
      return;
    }

    if (action === "rename") {
      if (!id || !presets[id] || !name) {
        res.status(400).json({ error: "존재하지 않는 설정이거나 이름이 비어있습니다." });
        return;
      }
      presets[id].name = name;
      await savePresets(presets);
      res.status(200).json({ ok: true });
      return;
    }

    if (action === "delete") {
      if (!id || !presets[id]) {
        res.status(400).json({ error: "존재하지 않는 설정입니다." });
        return;
      }
      delete presets[id];
      await savePresets(presets);
      res.status(200).json({ ok: true });
      return;
    }

    res.status(400).json({ error: "알 수 없는 action입니다." });
  } catch (e) {
    res.status(502).json({ error: String(e.message || e) });
  }
};
