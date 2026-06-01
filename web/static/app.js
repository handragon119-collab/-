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

// ---- 카테고리/주제/키커/톤 객관식 ----
let CATS = {};
let KICKERS = {};
let TONES = [];
let DEFAULT_KICKERS = [];
const CUSTOM = "✏️ 직접 입력";
const NONE = "(없음)";

function fillSelect(id, items, { custom = false, none = false } = {}) {
  const sel = $(id);
  sel.innerHTML = "";
  if (none) sel.appendChild(new Option(NONE, NONE));
  items.forEach((t) => sel.appendChild(new Option(t, t)));
  if (custom) sel.appendChild(new Option(CUSTOM, CUSTOM));
}

// 서버가 옛날 상태여도 카테고리가 항상 뜨도록 목록을 앱에 직접 내장
const LOCAL_OPTIONS = {
  topics: {
    "💰 금융·재테크": ["통장 쪼개기 4단계","사회초년생 첫 월급 관리법","비상금 모으는 법","신용점수 올리는 습관 5","연말정산 환급 늘리는 공제","ISA 계좌 절세 활용법","국민연금 더 받는 전략","2026 청년 지원금 총정리","복리와 72의 법칙","보험 리모델링 체크포인트","대출 갈아타기(대환) 전 확인","주택청약통장 활용법","파킹통장·CMA 비교","예금자보호 제대로 알기","30일 짠테크 챌린지"],
    "❤️ 연애·관계": ["첫 데이트 대화 주제","호감 신호 알아채는 법","권태기 극복하는 법","이별 후 마음 정리하기","썸에서 연애로 넘어가는 법","연락 빈도의 심리학","장거리 연애 유지 비법","결혼 전 꼭 맞춰볼 것","MBTI별 연애 스타일","싸우지 않는 대화법","재회 가능성 높이는 법","건강한 거리두기"],
    "🔮 운세·사주": ["2026 띠별 금전운","별자리별 성격 특징","MBTI별 연애운","행운을 부르는 습관","별자리 궁합 베스트","타로 입문 가이드","꿈 해몽 모음","이름으로 보는 성향","오늘의 행운 컬러","풍수 인테리어 기초","12지신 2026 총운","손금 보는 법 기초"],
    "🎬 연예·문화": ["아이돌 자기관리 루틴","무대 위 멘탈 관리법","발성·발음 연습 기초","오디션 합격 체크리스트","K팝 안무 연습 팁","콘서트 직관 꿀팁","팬덤 문화 용어 정리","셀럽 데일리룩 따라하기","데뷔 준비생 루틴","연예인 식단 관리 비결","촬영장 매너","공연 예매 성공 전략"],
    "🏠 생활·꿀팁": ["자취 필수템 리스트","냉장고 정리 노하우","빨래 얼룩 제거법","좁은 방 공간 활용","전기세 줄이는 법","헷갈리는 분리수거","곰팡이 제거·예방","옷 오래 입는 관리법","정리정돈 루틴","택배 안전하게 받기","집들이 선물 추천","생활 속 절약 습관"],
    "💪 건강·운동": ["거북목 탈출 스트레칭","아침 공복 습관","물 마시는 타이밍","홈트 초보 루틴","다이어트 정체기 극복","숙면을 위한 습관","눈 피로 푸는 법","단백질 똑똑하게 먹기","스트레스 해소법","면역력 높이는 음식","하루 만보 걷기 효과","폼롤러 사용법"],
    "📱 가전·IT": ["가성비 가전 고르는 법","스마트폰 배터리 오래 쓰기","와이파이 빠르게 하는 법","무선이어폰 고르기","로봇청소기 비교 포인트","공기청정기 관리법","느려진 노트북 살리기","스마트홈 입문","데이터 절약 설정","사진 안전하게 백업","보조배터리 고르는 법","TV 화질 설정 팁"],
    "🚀 자기계발": ["흔들리지 않는 아침 루틴","독서 습관 들이기","시간관리 4분면","집중력 높이는 법","미루는 습관 고치기","메모 잘하는 법","직장인 영어 공부 루틴","목표 제대로 세우기","번아웃 회복법","퇴근 후 1시간 활용법","자존감 높이는 말습관","21일 습관 만들기"],
    "✈️ 여행": ["국내 당일치기 코스","항공권 싸게 사는 법","캐리어 효율적으로 싸기","혼자 여행 준비물","해외여행 환전 꿀팁","여행 필수 앱 모음","제주 숨은 명소","해외여행 체크리스트","호캉스 200% 즐기기","여행 사진 잘 찍는 법","기차여행 추천 코스","비행기 좌석 고르기"],
    "🍳 음식·요리": ["자취 간단 요리","에어프라이어 레시피","다이어트 식단 짜기","계란 요리 10가지","밀프렙 시작하기","라면 맛있게 끓이는 법","남은 재료 활용 요리","5분 아침 메뉴","건강한 간식 추천","원팬 파스타","도시락 싸기 팁","김치 활용 레시피"],
    "👗 패션·뷰티": ["체형별 코디 공식","기본템 추천","피부타입별 스킨케어","모공 관리 루틴","데일리 메이크업","향수 고르는 법","헤어 손질 팁","계절별 코디","다크서클 케어","옷 잘 입는 법","손톱 관리법","안경 어울리게 쓰기"],
    "🐾 반려동물": ["강아지 분리불안 줄이기","고양이 화장실 교육","반려동물 응급처치 기초","산책 예절(펫티켓)","사료 고르는 법","털 빠짐 관리","반려동물 치아 관리","입양 전 체크리스트","이갈이 시기 장난감","더위·추위 대비법"],
    "💼 직장·커리어": ["이직 타이밍 잡기","자기소개서 잘 쓰는 법","면접 답변 공식","연봉협상 전략","직장 인간관계","보고 잘하는 법","회의 잘하는 법","워라밸 지키기","퇴사 전 체크리스트","첫 출근 준비물","링크드인 관리","사회초년생 매너"],
    "🏢 부동산": ["전세사기 예방법","청약 당첨 전략","등기부등본 보는 법","전월세 계약 체크리스트","헷갈리는 부동산 용어","내 집 마련 순서","깡통전세 피하기","중개수수료 계산법","이사 체크리스트"],
  },
  kickers: {
    "💰 금융·재테크": ["금융 가이드","재테크 꿀팁","돈 관리 노트","머니 클래스"],
    "❤️ 연애·관계": ["연애 가이드","연애 꿀팁","관계 노트","사랑 클래스"],
    "🔮 운세·사주": ["오늘의 운세","운세 가이드","사주 노트","행운 클래스"],
    "🎬 연예·문화": ["연예 이슈","컬처 가이드","스타 노트","엔터 클래스"],
    "🏠 생활·꿀팁": ["생활 꿀팁","살림 가이드","라이프 노트","꿀팁 클래스"],
    "💪 건강·운동": ["건강 가이드","헬스 꿀팁","웰니스 노트","바디 클래스"],
    "📱 가전·IT": ["IT 가이드","가전 꿀팁","테크 노트","디지털 클래스"],
    "🚀 자기계발": ["자기계발","성장 가이드","루틴 노트","마인드 클래스"],
    "✈️ 여행": ["여행 가이드","여행 꿀팁","트래블 노트","여행 클래스"],
    "🍳 음식·요리": ["오늘의 레시피","요리 꿀팁","쿠킹 노트","푸드 클래스"],
    "👗 패션·뷰티": ["뷰티 가이드","패션 꿀팁","스타일 노트","뷰티 클래스"],
    "🐾 반려동물": ["반려 가이드","펫 꿀팁","반려 노트","펫 클래스"],
    "💼 직장·커리어": ["커리어 가이드","직장 꿀팁","워크 노트","커리어 클래스"],
    "🏢 부동산": ["부동산 가이드","내집마련 꿀팁","부동산 노트","리얼티 클래스"],
  },
  tones: ["친근하고 신뢰감 있는","전문적이고 깔끔한","감성적이고 따뜻한","강렬하고 동기부여되는","유머러스하고 가벼운","차분하고 정보 중심의"],
  default_kickers: ["가이드","꿀팁","오늘의 정보"],
};

function applyOptions(o) {
  CATS = o.topics || {};
  KICKERS = o.kickers || {};
  TONES = o.tones || [];
  DEFAULT_KICKERS = o.default_kickers || [];
  fillSelect("category", Object.keys(CATS));
  $("category").onchange = () => { fillTopics(); fillKickers(); };
  fillSelect("tone-select", TONES, { custom: true });
  $("tone-select").onchange = () =>
    ($("tone").style.display = $("tone-select").value === CUSTOM ? "block" : "none");
  fillTopics();
  fillKickers();
}

async function loadOptions() {
  // 1) 항상 내장 목록으로 먼저 채운다 (서버가 옛날이어도 카테고리가 뜸)
  applyOptions(LOCAL_OPTIONS);
  // 2) 서버에 최신 목록이 있으면 덮어쓴다 (없어도 1번 덕분에 정상 동작)
  try {
    const o = await api("/api/options");
    if (o && o.topics && Object.keys(o.topics).length) applyOptions(o);
  } catch (e) { /* 무시: 내장 목록 사용 */ }
}

function fillTopics() {
  fillSelect("topic-select", CATS[$("category").value] || [], { custom: true });
  const sel = $("topic-select");
  sel.onchange = () =>
    ($("topic").style.display = sel.value === CUSTOM ? "block" : "none");
  sel.onchange();
}

function fillKickers() {
  const list = KICKERS[$("category").value] || DEFAULT_KICKERS;
  fillSelect("kicker-select", list, { custom: true, none: true });
  const sel = $("kicker-select");
  sel.onchange = () =>
    ($("kicker").style.display = sel.value === CUSTOM ? "block" : "none");
  sel.onchange();
}

function selectedTopic() {
  const sel = $("topic-select");
  return sel.value === CUSTOM ? $("topic").value.trim() : sel.value;
}
function selectedKicker() {
  const v = $("kicker-select").value;
  if (v === NONE) return null;
  if (v === CUSTOM) return $("kicker").value.trim() || null;
  return v;
}
function selectedTone() {
  const v = $("tone-select").value;
  return v === CUSTOM ? ($("tone").value.trim() || null) : v;
}

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
  const topic = selectedTopic();
  if (!topic) return toast("주제를 선택하거나 입력하세요", "err");
  const btn = $("btn-generate");
  btn.disabled = true;
  btn.textContent = "생성 중... (10~30초)";
  try {
    const payload = {
      topic,
      mode: $("mode").value,
      theme: $("theme").value,
      cards: parseInt($("cards").value) || 5,
      tone: selectedTone(),
      brand_handle: $("brand").value.trim() || null,
      agentic: $("agentic").checked,
      number: parseInt($("number").value) || null,
      kicker: selectedKicker(),
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
loadOptions();
loadSettings();
