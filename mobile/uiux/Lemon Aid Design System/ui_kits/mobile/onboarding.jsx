// onboarding.jsx — Pillyze-inspired multi-step onboarding for Lemon Aid.
// The flow takes the user from "hello" through profile + body metrics +
// HealthKit + dashboard customization, then drops them into the camera.
//
// State is held by OnboardingFlow; each step is a small subcomponent that
// reads + writes the same `data` object. The shell (OnboardingShell)
// handles the back button + progress bar + bottom CTA.
//
// All Pillyze purple references in the screenshots map to Lemon Aid's
// lemon (#FFCE00) and leaf (#6FCB73) — same liquid-glass 3D character
// style, but warm not cool.

const { useState: useStateO } = React;

// ── Data tables ───────────────────────────────────────────────────
const HEALTH_CONCERNS = [
  { id: "fatigue", label: "피로감",        icon: "battery-low",  badge: "30대 추천",
    grad: "linear-gradient(135deg, #BBE2FF, #4FA9F0)" },
  { id: "chronic", label: "만성질환 관리",  icon: "heart-pulse",  badge: "필수",
    grad: "linear-gradient(135deg, #FFB7B7, #E55E5E)" },
  { id: "liver",   label: "간 건강",        icon: "leaf",          badge: "30대 추천",
    grad: "linear-gradient(135deg, #FFCDCD, #E55E5E)" },
  { id: "chol",    label: "혈중 콜레스테롤", icon: "droplet",
    grad: "linear-gradient(135deg, #FFCDCD, #C8245F)" },
  { id: "eye",     label: "눈 건강",        icon: "eye",
    grad: "linear-gradient(135deg, #BBE2FF, #4FA9F0)" },
  { id: "muscle",  label: "운동 능력 & 근육량", icon: "dumbbell",
    grad: "linear-gradient(135deg, #D7F3DC, #6FCB73)" },
  { id: "bp",      label: "혈압",            icon: "activity",
    grad: "linear-gradient(135deg, #FFD4DF, #E94B7B)" },
  { id: "sleep",   label: "수면 & 스트레스", icon: "moon",
    grad: "linear-gradient(135deg, #FFEACC, #FFAA2E)" },
  { id: "immune",  label: "면역",            icon: "shield",
    grad: "linear-gradient(135deg, #E0D4FF, #9981E8)" },
];

const PURPOSES = [
  { id: "chronic",     label: "만성질환 관리",  icon: "heart-pulse",
    grad: "linear-gradient(135deg, #FFD4DF, #E94B7B)" },
  { id: "supplement",  label: "영양제 섭취 관리", icon: "pill",
    grad: "linear-gradient(135deg, var(--lemon-200), var(--lemon-500))" },
  { id: "diet",        label: "식단 관리 & 다이어트", icon: "utensils",
    grad: "linear-gradient(135deg, #FFE2AE, #E78A3A)" },
  { id: "blood",       label: "혈당 관리",        icon: "droplet",
    grad: "linear-gradient(135deg, #BBE2FF, #4FA9F0)" },
];

const STEP_LABELS = [
  "환영", "프로필", "목적", "건강 고민", "신체", "건강 연동", "식사 시간",
  "확인", "대시보드", "약관",
];
const TOTAL_STEPS = STEP_LABELS.length;

// ── Shell ─────────────────────────────────────────────────────────
function OnboardingShell({ step, onBack, children, cta, ctaDisabled, onCta, secondaryCta, onSecondary }) {
  return (
    <div className="lm-onboard">
      <header className="top">
        {step > 1 && (
          <button className="back" onClick={onBack} aria-label="back">
            <Icon name="chevron-left" />
          </button>
        )}
        <ProgressBar value={step} max={TOTAL_STEPS} />
        <span className="step">{step} / {TOTAL_STEPS}</span>
      </header>
      <div className="scroll">{children}</div>
      <div className="cta-bar">
        {secondaryCta && (
          <button className="b secondary" onClick={onSecondary} style={{ marginBottom: 8 }}>
            {secondaryCta}
          </button>
        )}
        {cta && (
          <button className="b" onClick={onCta} disabled={ctaDisabled}>
            {cta}
          </button>
        )}
      </div>
    </div>
  );
}

// ── Step 1 · Welcome ──────────────────────────────────────────────
const WELCOME_SLIDES = [
  { kicker: "BMI · 체질량지수",
    title: "체질량지수가 높아요.",
    body: "체질량지수(BMI)는 체지방량을 간접적으로 확인하는 방법이에요. 경계 범위에서는 BMI 관리만으로도 건강위험도를 낮출 수 있어요.",
    chart: "bmi" },
  { kicker: "Daily Brief · 오늘 한 줄",
    title: "단백질이 살짝 부족해요.",
    body: "AI Agent가 등록된 영양제·식단·활동량을 함께 보고, 오늘 어떤 영양소가 부족한지 한 줄로 알려드려요.",
    chart: "brief" },
  { kicker: "Photo · 사진 한 장으로",
    title: "라벨을 찍기만 하면 끝.",
    body: "영양제 라벨을 사진으로 찍거나 갤러리에서 선택하면, OCR과 KDRIs 기준으로 자동 분석해드려요.",
    chart: "photo" },
  { kicker: "Agent · 병원 기록 기억",
    title: "병원 기록을 기억하는 동반자.",
    body: "만성질환·복약·검사값을 함께 해석해 안전한 권고만 보여드려요. 진단·처방은 하지 않습니다.",
    chart: "agent" },
  { kicker: "Privacy · 안전한 처리",
    title: "10년치 건강 검진, 한눈에.",
    body: "데이터는 단말에서 먼저 처리되고, 동의 없이는 외부로 전송되지 않아요. 언제든 설정에서 변경할 수 있어요.",
    chart: "shield" },
];

function WelcomeStep({ go }) {
  const [carouselIdx, setIdx] = useStateO(0);
  return (
    <div className="lm-onboard">
      <div className="scroll" style={{ paddingTop: 64, gap: 18 }}>
        <Dots count={WELCOME_SLIDES.length} active={carouselIdx} />
        <Carousel value={carouselIdx} onChange={setIdx} interval={4800}>
          {WELCOME_SLIDES.map((s, i) => <WelcomeSlide key={i} {...s} />)}
        </Carousel>
        <div className="lm-coupon">
          <Icon name="sparkles" size={14} color="var(--lemon-500)" />
          지금 가입하시면 <b>첫 라벨 분석 무료</b> 쿠폰을 드려요
        </div>
      </div>
      <div className="cta-bar">
        <div className="lm-social-row" style={{ marginBottom: 14 }}>
          <button className="lm-social kakao" aria-label="kakao">
            <Icon name="message-circle" size={22} />
          </button>
          <button className="lm-social naver" aria-label="naver">N</button>
          <button className="lm-social apple" aria-label="apple">
            <Icon name="apple" size={22} />
          </button>
          <button className="lm-social email" aria-label="email" onClick={go}>
            <Icon name="mail" size={20} />
          </button>
        </div>
        <div style={{ textAlign: "center", font: "var(--t-body-sm)",
                       color: "var(--ink-500)", marginBottom: 24 }}>
          기업 회원이신가요? <u onClick={go} style={{ cursor: "pointer", color: "var(--ink-700)" }}>로그인</u>
        </div>
      </div>
    </div>
  );
}

function WelcomeSlide({ kicker, title, body, chart }) {
  return (
    <div style={{ textAlign: "center", padding: "0 4px" }}>
      <h1 style={{ margin: "8px 0 14px", font: "700 22px/1.35 var(--font-body)",
                    letterSpacing: "-0.005em" }}>
        {title}
      </h1>
      <div className="lm-mini-phone">
        <div className="badge">
          <Icon name={chartIcon(chart)} size={20} />
        </div>
        <div style={{ fontSize: 11, fontWeight: 700, color: "var(--ink-500)",
                        letterSpacing: "0.04em", textTransform: "uppercase" }}>
          {kicker}
        </div>
        <div style={{ font: "700 18px/1.2 var(--font-body)", margin: "4px 0 12px" }}>
          {title}
        </div>
        <SlideArt chart={chart} />
        <div style={{ marginTop: 14, font: "var(--t-body-sm)",
                        color: "var(--ink-700)", lineHeight: 1.5,
                        textAlign: "left" }}>
          <b style={{ color: "var(--lemon-600)" }}>이렇게 도와드려요</b><br/>
          {body}
        </div>
      </div>
    </div>
  );
}

function chartIcon(chart) {
  return ({
    bmi: "bar-chart-3", brief: "sparkles", photo: "camera",
    agent: "message-circle", shield: "shield-check",
  })[chart] || "info";
}

function SlideArt({ chart }) {
  if (chart === "bmi") return <MiniChart />;
  if (chart === "brief") return (
    <div style={{ display: "grid", gap: 8 }}>
      <div className="lm-pill lemon" style={{ alignSelf: "flex-start" }}>오늘 한 줄</div>
      <div style={{ font: "700 17px/1.3 var(--font-body)", color: "var(--ink-900)" }}>
        단백질이 살짝 부족해요.
      </div>
      <div style={{ height: 6, background: "rgba(214,158,0,0.15)",
                      borderRadius: 999, overflow: "hidden" }}>
        <div style={{ width: "82%", height: "100%",
                       background: "linear-gradient(90deg, var(--lemon-400), var(--leaf-400))" }} />
      </div>
      <div style={{ font: "var(--t-caption)", color: "var(--leaf-600)" }}>
        식단관리 점수 82 / 100
      </div>
    </div>
  );
  if (chart === "photo") return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr",
                    gap: 4, borderRadius: 12, overflow: "hidden" }}>
      {[
        ["#FFE680", "#F0B800"], ["#FFF4B0", "#E89C00"], ["#D7F3DC", "#6FCB73"],
        ["#FFE2AE", "#E78A3A"], ["#FFF8C7", "#FFCE00"], ["#FCD9C0", "#C76A3A"],
      ].map((g, i) => (
        <div key={i} style={{
          aspectRatio: "1", borderRadius: 6,
          background: `linear-gradient(135deg, ${g[0]}, ${g[1]})`,
        }} />
      ))}
    </div>
  );
  if (chart === "agent") return (
    <div style={{ display: "grid", gap: 6 }}>
      <div className="lm-bubble agent" style={{ alignSelf: "flex-start", maxWidth: "85%" }}>
        안녕하세요. 도움이 되는, 당신의 레몬에이드예요.
      </div>
      <div className="lm-bubble user" style={{ alignSelf: "flex-end", maxWidth: "75%" }}>
        오늘 비타민 D 더 먹어도 될까요?
      </div>
      <div className="lm-bubble agent" style={{ alignSelf: "flex-start", maxWidth: "85%" }}>
        등록한 영양제 두 종에서 비타민 D가 함께 들어 있어요. 약사님께 상담을 권해 드려요.
      </div>
    </div>
  );
  if (chart === "shield") return (
    <div style={{ display: "grid", placeItems: "center", padding: "12px 0" }}>
      <div style={{
        width: 80, height: 80, borderRadius: 22,
        background: "linear-gradient(135deg, var(--leaf-100), var(--leaf-500))",
        display: "grid", placeItems: "center", color: "#fff",
        boxShadow: "0 14px 22px rgba(31,138,74,0.30)",
      }}>
        <Icon name="shield-check" size={40} strokeWidth={1.8} />
      </div>
      <div style={{ marginTop: 12, display: "flex", gap: 6 }}>
        <span className="lm-pill success">단말 처리</span>
        <span className="lm-pill info">동의 우선</span>
        <span className="lm-pill review">언제든 해제</span>
      </div>
    </div>
  );
  return null;
}

function MiniChart() {
  return (
    <svg viewBox="0 0 240 90" width="100%" style={{ display: "block", height: "auto" }}>
      <defs>
        <linearGradient id="ch" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--lemon-300)"/>
          <stop offset="100%" stopColor="var(--lemon-500)"/>
        </linearGradient>
      </defs>
      <path d="M0,70 L60,55 L120,60 L180,30 L240,12"
            fill="none" stroke="url(#ch)" strokeWidth="2.4"
            strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx="0"   cy="70" r="3" fill="var(--leaf-500)"/>
      <circle cx="60"  cy="55" r="3" fill="var(--leaf-500)"/>
      <circle cx="120" cy="60" r="3" fill="var(--leaf-500)"/>
      <circle cx="180" cy="30" r="3" fill="var(--review)"/>
      <circle cx="240" cy="12" r="4" fill="var(--danger)"/>
      <text x="245" y="14" fontSize="9" fontWeight="700" fill="var(--danger)">35 비만</text>
      <text x="185" y="22" fontSize="8" fill="var(--review)">28 전 단계</text>
      <text x="125" y="74" fontSize="8" fill="var(--leaf-600)">24 정상</text>
      <g fontSize="7" fill="var(--ink-300)">
        <text x="0"   y="86">13.12</text>
        <text x="55"  y="86">18.12</text>
        <text x="115" y="86">20.12</text>
        <text x="175" y="86">21.11</text>
      </g>
    </svg>
  );
}

// ── Step 2 · Identity (name + DOB with iOS-style numeric keypad) ──
function IdentityStep({ data, set }) {
  // Tap on the DOB row makes the custom keypad active; tap elsewhere closes it.
  const [focused, setFocused] = useStateO("dob");
  const onKey = (k) => {
    if (k === "back") set({ dob: data.dob.slice(0, -1) });
    else if (k === "done") setFocused(null);
    else if (data.dob.length < 8) set({ dob: data.dob + k });
  };
  // Format YYYY.MM.DD as the user types.
  const formatted = data.dob.replace(/(\d{4})(\d{0,2})(\d{0,2})/, (_, a, b, c) =>
    [a, b, c].filter(Boolean).join("."));
  return (
    <>
      <div className="head">
        <h1>{data.name || "안녕하세요"}님의<br/>생일을 알려주세요.</h1>
        <p>권장 칼로리 · 영양 가이드라인은 만 나이에 따라 달라질 수 있어요.</p>
      </div>

      <div onClick={() => setFocused("dob")} style={{ cursor: "pointer" }}>
        <span className="lm-label" style={{
          color: focused === "dob" ? "var(--lemon-600)" : "var(--ink-500)",
          display: "block", marginBottom: 6,
        }}>
          생년월일 (8자리)
        </span>
        <div className="lm-input" style={{
          font: "600 18px/1 var(--font-body)",
          borderColor: focused === "dob" ? "var(--lemon-400)" : "var(--ink-200)",
          boxShadow: focused === "dob" ? "0 0 0 4px rgba(255,206,0,0.18)" : "none",
          minHeight: 22,
        }}>
          {formatted || <span style={{ color: "var(--ink-300)" }}>YYYY.MM.DD</span>}
          {focused === "dob" && (
            <span style={{ marginLeft: 2, color: "var(--lemon-600)",
                            animation: "lm-blink 1s steps(2, end) infinite" }}>|</span>
          )}
        </div>
      </div>

      <div onClick={() => setFocused("name")}>
        <span className="lm-label" style={{ color: "var(--ink-500)", display: "block", marginBottom: 6 }}>이름</span>
        <input
          className="lm-input"
          type="text"
          placeholder="홍길동"
          value={data.name}
          onFocus={() => setFocused("name")}
          onChange={(e) => set({ name: e.target.value })}
        />
      </div>

      {focused === "dob" && (
        <div style={{ margin: "10px -20px -16px" }}>
          <NumericKeypad onKey={onKey} />
        </div>
      )}
    </>
  );
}

// ── Step 3 · Purpose + Gender (two bottom sheets) ─────────────────
function PurposeStep({ data, set }) {
  const [openPurpose, setOpenP] = useStateO(false);
  const [openGender,  setOpenG] = useStateO(false);
  const purpose = PURPOSES.find(p => p.id === data.purpose);
  return (
    <>
      <div className="head">
        <h1>어떤 목적으로<br/>Lemon Aid를 찾아주셨나요?</h1>
        <p>응답에 따라 대시보드와 권장 영양 가이드라인이 달라져요.</p>
      </div>

      <DropdownField label="관심사 *" required value={purpose?.label}
        placeholder="목적을 선택해 주세요"
        onOpen={() => setOpenP(true)} />
      <DropdownField label="성별 *" required value={data.gender ? (data.gender === "m" ? "남성" : "여성") : ""}
        placeholder="성별을 선택해 주세요"
        onOpen={() => setOpenG(true)} />

      <BottomSheet open={openPurpose} title="어떤 목적으로 찾아주셨나요?"
                    desc="가장 가까운 한 가지만 선택해 주세요." onClose={() => setOpenP(false)}>
        {PURPOSES.map(p => (
          <div key={p.id} className={`opt ${data.purpose === p.id ? "selected" : ""}`}
                onClick={() => { set({ purpose: p.id }); setOpenP(false); }}>
            <span className="ico" style={{ background: p.grad }}>
              <Icon name={p.icon} size={16} color="#fff" />
            </span>
            {p.label}
          </div>
        ))}
      </BottomSheet>

      <BottomSheet open={openGender} title="성별은 어떻게 되시나요?"
                    desc="영양 가이드라인 계산에만 사용됩니다." onClose={() => setOpenG(false)}>
        <div className="gender-row">
          <div className={`gender m ${data.gender === "m" ? "selected" : ""}`}
                onClick={() => { set({ gender: "m" }); setOpenG(false); }}>
            <div className="icon-3d" style={{
              background: "linear-gradient(135deg, #BBE2FF, #4FA9F0)",
              color: "#fff",
            }}>
              <svg viewBox="0 0 24 24" width="32" height="32" fill="none"
                    stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
                <circle cx="10" cy="14" r="6"/>
                <path d="M15 9l6-6"/>
                <path d="M14 3h7v7"/>
              </svg>
            </div>
            남성 ♂
          </div>
          <div className={`gender f ${data.gender === "f" ? "selected" : ""}`}
                onClick={() => { set({ gender: "f" }); setOpenG(false); }}>
            <div className="icon-3d" style={{
              background: "linear-gradient(135deg, #FFD4DF, #E94B7B)",
              color: "#fff",
            }}>
              <svg viewBox="0 0 24 24" width="32" height="32" fill="none"
                    stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
                <circle cx="12" cy="9" r="6"/>
                <path d="M12 15v7"/>
                <path d="M9 19h6"/>
              </svg>
            </div>
            여성 ♀
          </div>
        </div>
      </BottomSheet>
    </>
  );
}

function DropdownField({ label, value, placeholder, onOpen }) {
  return (
    <div onClick={onOpen} style={{
      padding: "16px 14px", border: "1px solid var(--ink-200)",
      borderRadius: 14, background: "var(--paper)", cursor: "pointer",
      display: "grid", gap: 6,
    }}>
      <span style={{ font: "var(--t-label)",
                      color: value ? "var(--lemon-600)" : "var(--ink-500)" }}>
        {label}
      </span>
      <div style={{ display: "flex", alignItems: "center" }}>
        <span style={{ flex: 1, font: "600 15px/1 var(--font-body)",
                        color: value ? "var(--ink-900)" : "var(--ink-300)" }}>
          {value || placeholder}
        </span>
        <Icon name="chevron-down" size={18} color="var(--ink-300)" />
      </div>
    </div>
  );
}

// ── Step 4 · Health concerns grid ─────────────────────────────────
function ConcernsStep({ data, set }) {
  const selected = data.concerns || [];
  const toggle = (id) => {
    set({ concerns: selected.includes(id)
                     ? selected.filter(x => x !== id)
                     : [...selected, id].slice(0, 8) });
  };
  return (
    <>
      <div className="head">
        <h1>{data.name || "박준영"}님은 어떤<br/>건강 고민이 있으신가요?</h1>
        <p>최대 8개까지 선택 가능해요. 만성질환자에게 도움이 되는 권고를 우선해서 보여드려요.</p>
      </div>
      <div className="lm-concern-grid">
        {HEALTH_CONCERNS.map(c => (
          <ConcernCard key={c.id} icon={c.icon} label={c.label}
                       badge={c.badge} gradient={c.grad}
                       selected={selected.includes(c.id)}
                       onClick={() => toggle(c.id)} />
        ))}
      </div>
    </>
  );
}

// ── Step 5 · Body metrics (height + weight + target) ──────────────
function MetricsStep({ data, set }) {
  const [tab, setTab] = useStateO("height");
  return (
    <>
      <div className="head">
        <h1>{tab === "height" ? "키를 알려주세요"
            : tab === "weight" ? "몸무게를 알려주세요"
            : "목표 몸무게가 있으신가요?"}</h1>
        <p>{tab === "height" ? "정확한 권장 칼로리를 계산해 드릴게요."
            : tab === "weight" ? "몸무게에 따라 필요한 에너지량이 달라요."
            : "의료진·운동 전문가가 추천한 범위에서 직접 선택해 보세요."}</p>
      </div>
      <div style={{ display: "flex", gap: 4, background: "var(--canvas)",
                     borderRadius: 12, padding: 4 }}>
        {["height", "weight", "target"].map(t => (
          <span key={t} onClick={() => setTab(t)} style={{
            flex: 1, padding: "8px 0", textAlign: "center",
            font: "600 13px/1 var(--font-body)",
            color: tab === t ? "var(--ink-900)" : "var(--ink-500)",
            background: tab === t ? "var(--paper)" : "transparent",
            boxShadow: tab === t ? "var(--shadow-1)" : "none",
            borderRadius: 9, cursor: "pointer",
          }}>
            {t === "height" ? "키" : t === "weight" ? "현재 체중" : "목표"}
          </span>
        ))}
      </div>
      {tab === "height" && (
        <RulerPicker value={data.height} unit="cm" min={120} max={220} step={0.1}
                      onChange={(v) => set({ height: v })} />
      )}
      {tab === "weight" && (
        <RulerPicker value={data.weight} unit="kg" min={30} max={200} step={0.1}
                      onChange={(v) => set({ weight: v })} />
      )}
      {tab === "target" && (
        <>
          <RulerPicker value={data.target} unit="kg" min={30} max={200} step={0.1}
                        onChange={(v) => set({ target: v })} />
          <div style={{ background: "var(--lemon-50)",
                          border: "1px solid var(--lemon-100)",
                          borderRadius: 12, padding: 10, marginTop: 4,
                          font: "var(--t-body-sm)", color: "var(--ink-700)",
                          textAlign: "center" }}>
            키와 BMI 기준으로 추천하는 가장 건강한 몸무게는 <b style={{ color: "var(--lemon-600)" }}>62 kg ~ 71 kg</b> 이에요.
          </div>
        </>
      )}
    </>
  );
}

// ── Step 6 · HealthKit connection ─────────────────────────────────
function HealthKitStep({ data, set }) {
  return (
    <>
      <div className="head">
        <h1>건강 데이터를 연동해 주세요</h1>
        <p>활동량에 따라 권장 섭취 칼로리가 달라져요. 정확한 계산을 위해 HealthKit / Health Connect에서 안전하게 가져옵니다.</p>
      </div>
      <div style={{ display: "grid", placeItems: "center", padding: "20px 0" }}>
        <div style={{ position: "relative" }}>
          <div style={{
            width: 96, height: 96, borderRadius: 24,
            background: "linear-gradient(135deg, #FFE3EA, #FF5C7A)",
            display: "grid", placeItems: "center",
            boxShadow: "0 18px 28px rgba(255,92,122,0.36)",
          }}>
            <Icon name="heart" size={48} color="#fff" strokeWidth={1.6} />
          </div>
          <span style={{
            position: "absolute", right: -10, bottom: -8,
            width: 36, height: 36, borderRadius: 999,
            background: "var(--lemon-400)", color: "var(--ink-900)",
            display: "grid", placeItems: "center",
            boxShadow: "var(--shadow-2)",
          }}>
            <Icon name="link" size={16} strokeWidth={2.2} />
          </span>
        </div>
      </div>
      <div style={{ background: "var(--paper)", border: "1px solid var(--ink-100)",
                     borderRadius: 14, padding: "12px 16px" }}>
        {[
          ["footprints", "걸음수",   data.healthkit?.steps ?? true],
          ["heart-pulse", "심박수",  data.healthkit?.hr    ?? true],
          ["dumbbell",   "운동",     data.healthkit?.workout ?? true],
          ["scale",       "체중",    data.healthkit?.weight ?? false],
        ].map(([icon, label, on], i, arr) => (
          <div key={label} style={{
            display: "flex", alignItems: "center", gap: 10,
            padding: "10px 0",
            borderBottom: i < arr.length - 1 ? "1px solid var(--ink-100)" : "none",
          }}>
            <Icon name={icon} color="var(--lemon-500)" />
            <span style={{ flex: 1, font: "600 14px/1.2 var(--font-body)" }}>{label}</span>
            <Toggle on={on} />
          </div>
        ))}
      </div>
    </>
  );
}

// ── Step 7 · Meal time (3 collapsible rows + wheel picker) ────────
const HOURS = Array.from({ length: 12 }, (_, i) => String(i + 1).padStart(2, "0"));
const MINUTES = Array.from({ length: 12 }, (_, i) => String(i * 5).padStart(2, "0"));
const MERIDIEM = ["오전", "오후"];

function MealTimeStep({ data, set }) {
  const meals = data.meals || {
    breakfast: { m: "오전", h: "08", min: "00", skip: false },
    lunch:     { m: "오후", h: "12", min: "30", skip: false },
    dinner:    { m: "오후", h: "06", min: "30", skip: false },
  };
  const [open, setOpen] = useStateO("breakfast");
  const update = (key, patch) =>
    set({ meals: { ...meals, [key]: { ...meals[key], ...patch } } });

  const rows = [
    { id: "breakfast", icon: "sun",       label: "아침 식사", cls: "" },
    { id: "lunch",     icon: "sun-medium", label: "점심 식사", cls: "lunch" },
    { id: "dinner",    icon: "moon",      label: "저녁 식사", cls: "dinner" },
  ];

  return (
    <>
      <div className="head">
        <h1>식사 시간을 알려주세요</h1>
        <p>식사시간에 맞춰 영양제 알림과 식단 분석을 정확히 도와드릴게요.</p>
      </div>
      <div className="lm-meal">
        {rows.map((r, idx) => {
          const meal = meals[r.id];
          const opened = open === r.id;
          return (
            <React.Fragment key={r.id}>
              <div className={`row ${opened ? "open" : ""}`}
                   onClick={() => setOpen(opened ? null : r.id)}>
                <span className={`icon-3d ${r.cls}`}>
                  <Icon name={r.icon} size={16} color="#fff" strokeWidth={2} />
                </span>
                <span className="label">{r.label}</span>
                <span className="time">
                  {meal.skip ? "식사 안 함" : `${meal.h}:${meal.min} ${meal.m === "오전" ? "AM" : "PM"}`}
                </span>
                <span className="chev"><Icon name="chevron-down" size={16} /></span>
              </div>
              {opened && (
                <div className="body">
                  <div className="skip" onClick={() => update(r.id, { skip: !meal.skip })}
                        style={{ cursor: "pointer" }}>
                    <span className="box" style={{ background: meal.skip ? "var(--leaf-500)" : "var(--ink-200)" }}>
                      {meal.skip && <Icon name="check" size={11} strokeWidth={3} color="#fff" />}
                    </span>
                    식사 안 함
                  </div>
                  <WheelPicker columns={[
                    { id: "m",   items: MERIDIEM, value: meal.m,
                      onChange: v => update(r.id, { m: v }) },
                    { id: "h",   items: HOURS,    value: meal.h,
                      onChange: v => update(r.id, { h: v }) },
                    { id: "min", items: MINUTES,  value: meal.min,
                      onChange: v => update(r.id, { min: v }) },
                  ]} />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </>
  );
}

// ── Step 7 · Confirm review ───────────────────────────────────────
function ReviewStep({ data, set, go }) {
  const purpose = PURPOSES.find(p => p.id === data.purpose);
  const fields = [
    ["건강 고민", `${data.concerns.length === 0 ? "선택 안 함"
                    : (HEALTH_CONCERNS.find(c => c.id === data.concerns[0])?.label || "") +
                      (data.concerns.length > 1 ? ` 외 ${data.concerns.length - 1}개` : "")}`],
    ["관심사",    purpose?.label || "—"],
    ["성별",      data.gender === "m" ? "남성" : data.gender === "f" ? "여성" : "—"],
    ["생년월일",  data.dob ? `${data.dob.slice(0,4)}.${data.dob.slice(4,6)}.${data.dob.slice(6,8)}` : "—"],
    ["이름",      data.name || "—"],
    ["키 / 몸무게", `${data.height} cm / ${data.weight} kg`],
    ["목표 몸무게", `${data.target} kg`],
  ];
  return (
    <>
      <div className="head">
        <h1>정보가 모두 맞나요?</h1>
        <p>맞지 않으면 항목을 탭해서 수정할 수 있어요. 이후에도 설정에서 변경할 수 있어요.</p>
      </div>
      <div style={{ display: "grid", gap: 4 }}>
        {fields.map(([k, v]) => (
          <div key={k} style={{
            display: "grid", gap: 4, padding: "12px 0",
            borderBottom: "1px solid var(--ink-100)",
          }}>
            <span className="lm-label" style={{ color: "var(--ink-500)" }}>{k}</span>
            <div style={{ display: "flex", alignItems: "center" }}>
              <span style={{ flex: 1, font: "600 15px/1.2 var(--font-body)" }}>{v}</span>
              <Icon name="chevron-down" size={14} color="var(--ink-300)" />
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

// ── Step 8 · Customize dashboard cubes (drag to reorder) ───────────
function CubesStep({ data, set }) {
  const initialCubes = data.cubes || [
    { id: "supp",  label: "영양제",  value: "75% 완료", progress: 75,
      sub: "오후 08:00 · 멀티비타민데일리 외 1개", full: true },
    { id: "weight", label: "체중",  value: "55", unit: "kg" },
    { id: "fast",   label: "단식",  value: "1시간 20분", valueTone: "warn",
      sub: "진행 중" },
    { id: "diet",   label: "오늘 한 줄", value: "82", unit: "점",
      valueTone: "success", sub: "어제보다 +4점", full: true },
  ];
  const [cubes, setCubes] = useStateO(initialCubes);
  const hidden = [
    { id: "blood", name: "혈당", recommend: true },
    { id: "cond",  name: "컨디션" },
    { id: "water", name: "수분" },
    { id: "fomi",  name: "포미 다이어트" },
  ];
  const [showCoach, setCoach] = useStateO(true);
  const commit = (next) => { setCubes(next); set({ cubes: next }); };

  return (
    <>
      <div className="head">
        <p style={{ color: "var(--ink-500)" }}>아래 큐브를 움직여 보세요!</p>
        <h1 style={{ marginTop: 4 }}>나에게 딱 맞는<br/>건강 탭 만들기</h1>
        <span style={{ display: "inline-block",
                         background: "var(--lemon-100)", color: "var(--lemon-600)",
                         padding: "6px 12px", borderRadius: 999,
                         font: "600 13px/1 var(--font-body)" }}>
          {PURPOSES.find(p => p.id === data.purpose)?.label || "기본"} 추천 화면으로 구성했어요
        </span>
      </div>

      <ReorderList items={cubes} onReorder={commit}
                    renderItem={(c, isDragging) => (
        <Cube {...c}
              onRemove={() => commit(cubes.filter(x => x.id !== c.id))} />
      )} />

      <div style={{ marginTop: 18 }}>
        <span className="lm-label" style={{ color: "var(--ink-500)" }}>숨긴 항목</span>
        {hidden.map(h => (
          <div key={h.id} className="lm-add-row">
            <span className="name">{h.name}</span>
            {h.recommend && <span className="pill">관리 추천</span>}
            <button className="add" aria-label="add">+</button>
          </div>
        ))}
      </div>

      {showCoach && (
        <div onClick={() => setCoach(false)} style={{ cursor: "pointer" }}>
          <CoachMark
            title="큐브를 길게 눌러 끌어보세요!"
            body="원하는 순서로 자유롭게 재배치할 수 있어요."
          />
        </div>
      )}
    </>
  );
}

// ── Step 9 · Terms agreement ──────────────────────────────────────
function TermsStep({ data, set }) {
  const t = data.terms || { age: false, tos: false, privacy: false, sensitive: false, marketing: false };
  const required = ["age", "tos", "privacy", "sensitive"];
  const allRequired = required.every(k => t[k]);
  const allOn = ["age", "tos", "privacy", "sensitive", "marketing"].every(k => t[k]);
  const toggleAll = () => {
    const next = !allOn;
    set({ terms: { age: next, tos: next, privacy: next, sensitive: next, marketing: next } });
  };
  const toggle = (k) => set({ terms: { ...t, [k]: !t[k] } });
  return (
    <>
      <div className="head">
        <h1>약관에 동의해 주세요</h1>
        <p>여러분의 개인정보와 서비스 이용 권리를 잘 지켜드릴게요.</p>
      </div>
      <div className="lm-row" onClick={toggleAll} style={{ cursor: "pointer" }}>
        <CheckCircle on={allOn} />
        <div style={{ flex: 1 }}>
          <div style={{ font: "700 15px/1.2 var(--font-body)" }}>모두 동의</div>
          <small>약관 및 개인정보보호방침, 마케팅 수신에 동의합니다.</small>
        </div>
      </div>
      {[
        ["age",       true,  "(필수) 만 14세 이상이에요"],
        ["tos",       true,  "(필수) 서비스 이용약관 동의"],
        ["privacy",   true,  "(필수) 개인정보보호방침 동의"],
        ["sensitive", true,  "(필수) 민감정보 수집 및 이용동의"],
        ["marketing", false, "(선택) 마케팅 수신 동의"],
      ].map(([k, req, label]) => (
        <div key={k} onClick={() => toggle(k)} style={{
          display: "flex", alignItems: "center", gap: 12, padding: "14px 0",
          borderBottom: "1px solid var(--ink-100)", cursor: "pointer",
        }}>
          <CheckCircle on={t[k]} />
          <span style={{ flex: 1, font: "500 14px/1.2 var(--font-body)",
                          color: t[k] ? "var(--ink-900)" : "var(--ink-500)" }}>
            {label}
          </span>
          <small style={{ color: "var(--ink-300)" }}>보기 ›</small>
        </div>
      ))}
      {!allRequired && (
        <small style={{ color: "var(--danger)", marginTop: 6 }}>
          필수 약관 4개에 모두 동의해야 진행할 수 있어요.
        </small>
      )}
    </>
  );
}

function CheckCircle({ on }) {
  return (
    <span style={{
      width: 22, height: 22, borderRadius: 999,
      background: on ? "var(--lemon-400)" : "var(--ink-100)",
      color: on ? "var(--ink-900)" : "var(--ink-300)",
      display: "grid", placeItems: "center", flexShrink: 0,
      transition: "background 180ms",
    }}>
      <Icon name="check" size={13} strokeWidth={3} />
    </span>
  );
}

// ── Orchestrator ──────────────────────────────────────────────────
function OnboardingFlow({ state, setState, go }) {
  const [step, setStep] = useStateO(1);
  const [data, setData] = useStateO({
    name: "박준영", dob: "20010828",
    gender: null, purpose: null,
    concerns: [],
    height: 175.2, weight: 73.6, target: 70.0,
    healthkit: { steps: true, hr: true, workout: true, weight: false },
    cubes: null,
    terms: { age: false, tos: false, privacy: false, sensitive: false, marketing: false },
  });
  const set = (patch) => setData(d => ({ ...d, ...patch }));
  const next = () => setStep(s => Math.min(TOTAL_STEPS, s + 1));
  const back = () => setStep(s => Math.max(1, s - 1));

  // Step 1 has its own chrome (no progress bar).
  if (step === 1) {
    return <WelcomeStep go={() => setStep(2)} />;
  }

  // Validation per step.
  const canAdvance = () => {
    if (step === 2) return data.name && /^\d{8}$/.test(data.dob);
    if (step === 3) return data.purpose && data.gender;
    if (step === 4) return data.concerns.length > 0;
    if (step === 8) return true;
    if (step === 10) return ["age","tos","privacy","sensitive"].every(k => data.terms[k]);
    return true;
  };

  const cta = step === 10 ? "가입 완료"
            : step === 8  ? "확인했어요"
            : step === 9  ? "편집 완료"
            : step === 6  ? "지금 연동하기"
            : "다음";
  const secondary = step === 6 ? "나중에 연동할게요" : null;

  // Finishing: drop into the camera.
  const finish = () => {
    setState(s => ({
      ...s,
      consents: {
        ocr: true,
        health: !!data.terms.sensitive,
        health_connect: !!data.healthkit?.steps,
        learning: !!data.terms.marketing,
      },
      profile: data,
    }));
    go("capture");
  };

  const onCta = () => {
    if (step === TOTAL_STEPS) finish();
    else next();
  };

  let body;
  if      (step === 2) body = <IdentityStep   data={data} set={set} />;
  else if (step === 3) body = <PurposeStep    data={data} set={set} />;
  else if (step === 4) body = <ConcernsStep   data={data} set={set} />;
  else if (step === 5) body = <MetricsStep    data={data} set={set} />;
  else if (step === 6) body = <HealthKitStep  data={data} set={set} />;
  else if (step === 7) body = <MealTimeStep   data={data} set={set} />;
  else if (step === 8) body = <ReviewStep     data={data} set={set} go={go} />;
  else if (step === 9) body = <CubesStep      data={data} set={set} />;
  else if (step === 10) body = <TermsStep     data={data} set={set} />;

  return (
    <OnboardingShell
      step={step} onBack={back}
      cta={cta} ctaDisabled={!canAdvance()} onCta={onCta}
      secondaryCta={secondary} onSecondary={finish}
    >
      {body}
    </OnboardingShell>
  );
}

Object.assign(window, {
  OnboardingFlow, WelcomeStep, IdentityStep, PurposeStep, ConcernsStep,
  MetricsStep, HealthKitStep, MealTimeStep, ReviewStep, CubesStep, TermsStep,
  HEALTH_CONCERNS, PURPOSES, STEP_LABELS, TOTAL_STEPS, CheckCircle,
  WELCOME_SLIDES, WelcomeSlide, SlideArt, HOURS, MINUTES, MERIDIEM,
});
