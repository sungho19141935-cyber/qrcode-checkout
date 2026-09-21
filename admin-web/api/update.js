// POST /api/update — 비밀번호 인증 후 Gist의 checkout_url/checkout_time을 갱신
const { verifyPassword } = require("./_auth");

const VALID_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    res.status(405).json({ error: "POST만 허용됩니다." });
    return;
  }

  const { password, checkout_time, checkout_times, qr_image, active_days, after_close_url, schedule } =
    req.body || {};

  let passwordOk;
  try {
    passwordOk = password ? await verifyPassword(password) : false;
  } catch (e) {
    res.status(500).json({ error: String(e.message || e) });
    return;
  }
  if (!passwordOk) {
    res.status(401).json({ error: "비밀번호가 올바르지 않습니다." });
    return;
  }

  const TIME_RE = /^([01]\d|2[0-3]):[0-5]\d$/;
  const IMAGE_RE = /^data:image\/(png|jpeg|jpg|webp);base64,/;
  const URL_RE = /^https?:\/\//;

  // 새 형식은 시각마다 QR/링크를 따로 가진다. 구 형식(공용 QR + 시각 목록)도 그대로 받는다.
  let entries;
  if (Array.isArray(schedule) && schedule.length) {
    entries = schedule.map((e) => ({
      time: String((e && e.time) || "").trim(),
      qr_image: (e && e.qr_image) || "",
      after_close_url: String((e && e.after_close_url) || "").trim(),
    }));
  } else {
    const rawTimes = Array.isArray(checkout_times)
      ? checkout_times
      : String(checkout_times || checkout_time || "").split(",");
    entries = [...new Set(rawTimes.map((t) => String(t).trim()).filter(Boolean))].map((t) => ({
      time: t,
      qr_image: qr_image || "",
      after_close_url: String(after_close_url || "").trim(),
    }));
  }

  if (!entries.length) {
    res.status(400).json({ error: "퇴실 시각을 최소 하나는 등록하세요." });
    return;
  }
  if (entries.length > 10) {
    res.status(400).json({ error: "퇴실 시각은 최대 10개까지 등록할 수 있습니다." });
    return;
  }

  for (const e of entries) {
    if (!TIME_RE.test(e.time)) {
      res.status(400).json({ error: `퇴실 시각은 HH:MM 형식이어야 합니다: "${e.time}"` });
      return;
    }
    if (!e.qr_image) {
      res.status(400).json({ error: `${e.time}에 표시할 QR 이미지를 등록하세요.` });
      return;
    }
    if (!IMAGE_RE.test(e.qr_image)) {
      res.status(400).json({ error: `${e.time}의 QR은 이미지 파일이어야 합니다.` });
      return;
    }
    if (e.after_close_url && !URL_RE.test(e.after_close_url)) {
      res.status(400).json({ error: `${e.time}의 링크는 http:// 또는 https://로 시작해야 합니다.` });
      return;
    }
  }

  // 같은 시각이 두 번 등록되면 어느 쪽이 뜰지 알 수 없으므로 막는다
  const dupe = entries.map((e) => e.time).find((t, i, arr) => arr.indexOf(t) !== i);
  if (dupe) {
    res.status(400).json({ error: `같은 시각이 두 번 등록되었습니다: ${dupe}` });
    return;
  }

  entries.sort((a, b) => a.time.localeCompare(b.time));

  // Vercel Serverless Function 요청 본문 한도(4.5MB)를 넘지 않도록 여유를 두고 제한
  const totalBytes = entries.reduce((n, e) => n + e.qr_image.length, 0);
  if (totalBytes > 3_500_000) {
    res.status(400).json({
      error: "등록한 이미지 용량 합계가 너무 큽니다. 더 작은 이미지(스크린샷 크롭 등)를 사용하세요.",
    });
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

  // 구버전 학생 프로그램(자동 업데이트 전)은 schedule을 모르고 시각 하나만 읽는다.
  // 이때 가장 이른 시각을 주면 점심 퇴실 같은 앞 항목이 대표가 되어, 정작 중요한
  // 마지막 퇴실을 놓친다. 그래서 마지막 시각을 기존 형식으로 남긴다.
  const legacy = entries[entries.length - 1];
  const content = JSON.stringify(
    {
      schedule: entries,
      qr_image: legacy.qr_image,
      checkout_time: legacy.time,
      checkout_times: entries.map((e) => e.time),
      active_days: days,
      after_close_url: legacy.after_close_url,
    },
    null,
    2
  );

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
