// ---- 공통 ----
const $ = (id) => document.getElementById(id);
let currentJob = null;

function toast(msg, kind = "") {
  const t = $("toast");
  t.textContent = msg;
  t.className = "toast " + kind;
  setTimeout(() => (t.className = "toast hidden"), 3200);
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "요청 실패");
  return data;
}

// ---- 탭 전환 ----
document.querySelectorAll(".tab").forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    $("tab-" + btn.dataset.tab).classList.add("active");
  };
});

// ---- 설정 로드/저장 ----
const SETTING_IDS = [
  "publisher", "ig_graph_access_token", "ig_graph_user_id",
  "caption_provider", "gemini_api_key", "anthropic_api_key",
  "image_host", "imgbb_api_key",
];

async function loadSettings() {
  try {
    const s = await api("/api/settings");
    SETTING_IDS.forEach((k) => {
      const el = $("s-" + k);
      if (el && s[k] !== undefined && s[k] !== "") el.value = s[k];
    });
    if (s.brand_handle) $("brand").value = s.brand_handle;
    if (s.card_theme) $("theme").value = s.card_theme;
  } catch (e) {}
}

$("btn-save").onclick = async () => {
  const data = {};
  SETTING_IDS.forEach((k) => {
    const el = $("s-" + k);
    if (el) data[k] = el.value;
  });
  // 비밀값이 마스크(********) 그대로면 변경 안 함 → 서버가 무시
  try {
    await api("/api/settings", { method: "POST", body: JSON.stringify({ data }) });
    $("save-result").className = "result ok";
    $("save-result").textContent = "✓ 저장되었습니다.";
    toast("설정 저장 완료", "ok");
  } catch (e) {
    $("save-result").className = "result err";
    $("save-result").textContent = "저장 실패: " + e.message;
  }
};

// ---- 연결 테스트 ----
$("btn-test").onclick = async () => {
  $("test-result").className = "result";
  $("test-result").textContent = "확인 중...";
  try {
    // 먼저 현재 폼값 저장 후 테스트
    await $("btn-save").onclick();
    const r = await api("/api/test-connection");
    if (r.ok && r.method === "graph") {
      $("test-result").className = "result ok";
      $("test-result").innerHTML =
        `✓ 연결됨: <b>@${r.username}</b> · 팔로워 ${r.followers ?? "-"} · 게시물 ${r.media_count ?? "-"}`;
      setBadge(true, r.username);
    } else {
      $("test-result").className = "result ok";
      $("test-result").textContent = "✓ " + (r.note || "연결 확인됨");
      setBadge(r.ok, null);
    }
  } catch (e) {
    $("test-result").className = "result err";
    $("test-result").textContent = "✗ " + e.message;
    setBadge(false);
  }
};

function setBadge(on, name) {
  const b = $("conn-badge");
  if (on) {
    b.className = "badge badge-on";
    b.textContent = name ? "@" + name + " 연결됨" : "계정 연결됨";
  } else {
    b.className = "badge badge-off";
    b.textContent = "계정 미연결";
  }
}

// ---- 생성 ----
$("btn-generate").onclick = generate;
$("btn-regen").onclick = generate;

async function generate() {
  const topic = $("topic").value.trim();
  if (!topic) return toast("주제를 입력하세요", "err");
  const btn = $("btn-generate");
  btn.disabled = true;
  btn.textContent = "생성 중... (10~30초)";
  try {
    const payload = {
      topic,
      mode: $("mode").value,
      theme: $("theme").value,
      cards: parseInt($("cards").value) || 5,
      tone: $("tone").value.trim() || null,
      brand_handle: $("brand").value.trim() || null,
      agentic: $("agentic").checked,
      number: parseInt($("number").value) || null,
      kicker: $("kicker").value.trim() || null,
    };
    const r = await api("/api/generate", { method: "POST", body: JSON.stringify(payload) });
    currentJob = r.job_id;
    renderPreview(r);
    toast("생성 완료!", "ok");
  } catch (e) {
    toast("생성 실패: " + e.message, "err");
  } finally {
    btn.disabled = false;
    btn.textContent = "✨ 생성하기";
  }
}

function renderPreview(r) {
  $("preview-empty").classList.add("hidden");
  $("preview").classList.remove("hidden");
  const slides = $("slides");
  slides.innerHTML = "";
  r.images.forEach((src) => {
    const img = document.createElement("img");
    img.src = src + "?t=" + Date.now();
    slides.appendChild(img);
  });
  $("caption").value = r.full_text;

  const rep = $("agent-report");
  if (r.agent_report) {
    const a = r.agent_report;
    rep.classList.remove("hidden");
    rep.innerHTML =
      `<b>🤖 에이전트 리포트</b><br/>` +
      a.steps.map((s) => `<span class="chip">${s}</span>`).join("") +
      `<br/>웹검색: <b>${a.web_search_used ? "ON" : "미사용(내장지식)"}</b>` +
      ` · 근거 기관: <b>${(a.sources || []).join(", ") || "-"}</b>` +
      (a.risk_flags && a.risk_flags.length
        ? ` · ⚠️ 리스크: ${a.risk_flags.join(", ")}` : " · 리스크 없음");
  } else {
    rep.classList.add("hidden");
  }
}

// ---- 발행 ----
$("btn-publish").onclick = async () => {
  if (!currentJob) return toast("먼저 콘텐츠를 생성하세요", "err");
  if (!confirm("이 콘텐츠를 인스타그램에 지금 발행할까요?")) return;
  const btn = $("btn-publish");
  btn.disabled = true;
  btn.textContent = "발행 중...";
  try {
    const r = await api("/api/publish", {
      method: "POST",
      body: JSON.stringify({ job_id: currentJob, caption: $("caption").value }),
    });
    toast("🎉 발행 완료: " + r.result, "ok");
  } catch (e) {
    toast("발행 실패: " + e.message, "err");
  } finally {
    btn.disabled = false;
    btn.textContent = "🚀 지금 발행";
  }
}

// ---- 초기화 ----
loadSettings();
