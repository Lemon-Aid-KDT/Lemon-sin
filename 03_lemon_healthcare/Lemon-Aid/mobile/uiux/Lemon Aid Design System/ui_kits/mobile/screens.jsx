// screens.jsx — Lemon Aid mobile UI kit screens.
// Click-through flows that use the components defined in components.jsx.
// Each screen takes `{ go, state, setState }` props from App.jsx.

const { useState: useStateS, useEffect: useEffectS, useRef: useRefS } = React;

// ── Sample data — what the demo populates by default ─────────────
const DEMO_SUPPLEMENTS = [
  { id: "s1", name: "오메가-3 골드",      time: "아침",  count: 8 },
  { id: "s2", name: "비타민 D 1000IU",     time: "점심",  count: 1 },
  { id: "s3", name: "마그네슘 350",         time: "저녁",  count: 2 },
];

const DEMO_INGREDIENTS = [
  { id: "i1", name: "비타민 D", amount: 800, unit: "IU", confidence: 0.92, status: "ok" },
  { id: "i2", name: "오메가-3 (EPA+DHA)", amount: 1000, unit: "mg", confidence: 0.88, status: "ok" },
  { id: "i3", name: "비타민 E", amount: 12, unit: "mg α-TE", confidence: 0.62, status: "review" },
  { id: "i4", name: "아연", amount: 15, unit: "mg", confidence: 0.79, status: "dup" },
];

// ── Gallery library — what shows up in the iOS photos picker. ────
// Mixes real mascot frames (acting as "previously taken" label shots)
// with gradient placeholders that simulate supplement & food photos.
// Each item carries metadata so the picker can show "촬영 일시 · 위치 · 라벨 인식".
const GALLERY_LIBRARY = [
  { id: "g01", kind: "label",  album: "labels", label: "오메가-3",
    date: "2026.05.18", time: "08:42", loc: "자택", isLabel: true, fav: true,
    grad: ["#FFE680","#FFB400"] },
  { id: "g02", kind: "label",  album: "labels", label: "비타민 D",
    date: "2026.05.17", time: "21:08", loc: "자택", isLabel: true,
    grad: ["#FFF4B0","#E89C00"] },
  { id: "g03", kind: "mascot", album: "labels",
    src: lmRes("mIdle", "../../assets/mascot/tablet-frames/00-idle.png"),
    date: "2026.05.17", time: "19:33", loc: "약국 (북구)", live: true, isLabel: true,
    label: "약 봉투" },
  { id: "g04", kind: "label",  album: "labels", label: "마그네슘",
    date: "2026.05.16", time: "12:15", loc: "사무실", isLabel: true,
    grad: ["#D7F3DC","#6FCB73"] },
  { id: "g05", kind: "food",   album: "meals",  label: "닭가슴살 샐러드",
    date: "2026.05.18", time: "12:31", loc: "사무실 · 한솥도시락", fav: true,
    grad: ["#FFE2AE","#E78A3A"] },
  { id: "g06", kind: "food",   album: "meals",  label: "현미밥",
    date: "2026.05.18", time: "08:10", loc: "자택",
    grad: ["#F4E6BE","#C49443"] },
  { id: "g07", kind: "label",  album: "labels", label: "프로바이오틱",
    date: "2026.05.15", time: "22:04", loc: "자택", isLabel: true,
    grad: ["#FFF8C7","#FFCE00"] },
  { id: "g08", kind: "mascot", album: "all",
    src: lmRes("mGoldPoster", "../../assets/mascot/gold-poster.png"),
    date: "2026.05.14", time: "15:50", loc: "자택" },
  { id: "g09", kind: "food",   album: "meals",  label: "오트밀",
    date: "2026.05.14", time: "07:48", loc: "자택",
    grad: ["#F1E1B8","#A67B3E"] },
  { id: "g10", kind: "label",  album: "labels", label: "종합비타민",
    date: "2026.05.13", time: "10:22", loc: "약국 (북구)", isLabel: true, fav: true,
    grad: ["#FFE680","#F0B800"] },
  { id: "g11", kind: "food",   album: "meals",  label: "구운 연어",
    date: "2026.05.12", time: "19:05", loc: "본가 · 어머니댁",
    grad: ["#FFD3B0","#D86A2A"] },
  { id: "g12", kind: "mascot", album: "all",
    src: lmRes("mLeafComplete", "../../assets/mascot/tablet-frames/03-leaf-complete.png"),
    date: "2026.05.10", time: "13:24", loc: "자택" },
  { id: "g13", kind: "label",  album: "labels", label: "콜라겐 펩타이드",
    date: "2026.05.10", time: "09:01", loc: "자택", isLabel: true,
    grad: ["#FFF8C7","#E0B055"] },
  { id: "g14", kind: "food",   album: "meals",  label: "두부",
    date: "2026.05.09", time: "18:40", loc: "자택",
    grad: ["#FFF4D8","#C0AB6B"] },
  { id: "g15", kind: "label",  album: "labels", label: "철분 + 비오틴",
    date: "2026.05.08", time: "16:55", loc: "한약방 (동성로)", isLabel: true,
    grad: ["#FCD9C0","#C76A3A"] },
];

const ALBUMS = [
  { id: "all",      name: "모든 사진",     getCount: lib => lib.length },
  { id: "favs",     name: "즐겨찾기",       getCount: lib => lib.filter(i => i.fav).length },
  { id: "recents",  name: "최근 항목",       getCount: lib => Math.min(lib.length, 12) },
  { id: "labels",   name: "영양제 라벨",     getCount: lib => lib.filter(i => i.album === "labels").length },
  { id: "meals",    name: "식단 사진",       getCount: lib => lib.filter(i => i.album === "meals").length },
];

// ─────────────────────────────────────────────────────────────────
// OnboardingScreen — first-launch consent gate. Splash + mascot +
//                    two required consents + the agent's opening line.
// ─────────────────────────────────────────────────────────────────
function OnboardingScreen({ state, setState, go }) {
  const ocr   = state.consents.ocr;
  const heal  = state.consents.health;
  const ready = ocr && heal;

  const toggle = key => setState(s => ({
    ...s, consents: { ...s.consents, [key]: !s.consents[key] },
  }));

  return (
    <div className="lm-screen" style={{ background:
      "linear-gradient(180deg, #FFFDF6 0%, #FFF4B0 75%, #FFE57A 100%)" }}>
      <div className="lm-scroll" style={{ paddingTop: 60, paddingBottom: 24 }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
          <Mascot pose="idle" size={172} />
          <Wordmark size={36} />
          <p style={{ margin: 0, font: "var(--t-body-lg)", color: "var(--ink-700)",
                       textAlign: "center", maxWidth: 280 }}>
            도움이 되는, <b style={{ color: "var(--ink-900)" }}>당신의 레몬에이드</b>.
            사진 한 장으로 영양제와 식단을 함께 살펴봅니다.
          </p>
        </div>

        <div style={{ marginTop: 28, display: "grid", gap: 10 }}>
          <ConsentRow
            label="라벨 이미지 OCR 처리"
            sub="사진에서 텍스트만 추출합니다. 원본 이미지는 저장하지 않습니다."
            granted={ocr}
            onToggle={() => toggle("ocr")}
          />
          <ConsentRow
            label="민감 건강정보 분석"
            sub="만성질환·복약 데이터를 함께 해석합니다. 외부에 전송되지 않습니다."
            granted={heal}
            onToggle={() => toggle("health")}
          />
        </div>

        <Disclaimer tone="lemon" icon="sparkles">
          <b>안녕하세요. 도움이 되는, 당신의 레몬에이드예요.</b><br/>
          AI는 거드는 손길이에요. 분석 결과는 저장 전에 다시 보여드릴게요.
        </Disclaimer>
      </div>
      <div style={{ position: "absolute", left: 16, right: 16, bottom: 56,
                    display: "grid", gap: 8, zIndex: 6 }}>
        <Button
          variant="primary" block icon="arrow-right"
          disabled={!ready}
          onClick={() => go("capture")}
        >
          {ready ? "시작하기" : "두 항목 모두 동의해 주세요"}
        </Button>
      </div>
    </div>
  );
}

function ConsentRow({ label, sub, granted, onToggle }) {
  return (
    <div className="lm-row" onClick={onToggle} style={{ cursor: "pointer" }}>
      <div style={{ flex: 1 }}>
        <div style={{ font: "600 15px/1.2 var(--font-body)", color: "var(--ink-900)" }}>
          {label}
        </div>
        <div style={{ font: "var(--t-body-sm)", color: "var(--ink-500)", marginTop: 2 }}>
          {sub}
        </div>
      </div>
      <Toggle on={granted} />
    </div>
  );
}

function Toggle({ on }) {
  return (
    <span style={{
      width: 44, height: 26, borderRadius: 999,
      background: on ? "var(--leaf-600)" : "var(--ink-200)",
      transition: "background 200ms", position: "relative",
      flexShrink: 0,
    }}>
      <span style={{
        position: "absolute", top: 2, left: on ? 20 : 2,
        width: 22, height: 22, borderRadius: 999,
        background: "white", boxShadow: "0 1px 2px rgba(0,0,0,0.18)",
        transition: "left 220ms cubic-bezier(0.32,0.72,0,1)",
      }} />
    </span>
  );
}

// ─────────────────────────────────────────────────────────────────
// DashboardScreen — the home tab. Today's brief + four metric tiles
//                    + recent supplements + disclaimer.
//                    On first visit, run a coach-mark sequence.
// ─────────────────────────────────────────────────────────────────
function DashboardScreen({ state, setState, go }) {
  // The flow finishes onboarding, lands on home, and the agent walks the
  // user through the dashboard for the first time. After the user dismisses
  // it, we record `seenDashCoach` so it doesn't fire again.
  const showCoach = !state.seenDashCoach;
  const finishCoach = () => setState(s => ({ ...s, seenDashCoach: true }));
  const rootRef = React.useRef(null);

  return (
    <div className="lm-screen" ref={rootRef}>
      <AppBar
        title="오늘"
        subtitle="2026.05.18 · 09:24 갱신"
        right={
          <button style={{ padding: 6, background: "transparent", border: "none",
                            color: "var(--ink-700)" }} aria-label="refresh">
            <Icon name="refresh-ccw" />
          </button>
        }
      />
      <div className="lm-scroll">
        {/* Glass hero card — today's one-line brief */}
        <Card glass style={{ marginTop: 12 }} data-coach="brief">
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <Pill tone="lemon" icon="sparkles">오늘 한 줄</Pill>
            <span style={{ marginLeft: "auto", font: "var(--t-caption)",
                            color: "var(--ink-500)" }}>
              레몬에이드 Agent
            </span>
          </div>
          <h2 style={{ margin: "0 0 6px", font: "var(--t-h2)", letterSpacing: "-0.01em" }}>
            단백질이 살짝 부족해요.
          </h2>
          <p style={{ margin: 0, color: "var(--ink-700)" }}>
            점심에 가벼운 단백질 한 조각을 더해 보세요. 어제보다 식단 점수가
            4점 올라갔어요.
          </p>
          <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 8 }}>
            <div className="lm-progress-bar" style={{ flex: 1 }} />
            <span style={{ font: "var(--t-label)", color: "var(--leaf-700)" }}>
              82 / 100
            </span>
          </div>
        </Card>

        <SectionHeader kicker="DAILY SUMMARY" title="다섯 가지 산출" right={
          <button style={{ background: "transparent", border: "none",
                            color: "var(--ink-500)", font: "var(--t-label)",
                            cursor: "pointer" }}>
            전체 보기 ›
          </button>
        } />

        <div data-coach="tiles" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <Tile icon="trending-down" iconBg="var(--leaf-50)" iconColor="var(--leaf-600)"
                label="부족 영양소" value="3" unit="종" meta="단백질 · 칼슘 · 철" />
          <Tile icon="trending-up" iconBg="var(--warning-soft)" iconColor="#7A4200"
                label="과다 섭취" value="1" unit="종" meta="비타민 C 중복" />
          <Tile icon="shield-alert" iconBg="var(--review-soft)" iconColor="var(--review)"
                label="주의 성분" value="2" unit="건" meta="와파린 상호작용" />
          <Tile icon="award" iconBg="var(--lemon-100)" iconColor="var(--lemon-600)"
                label="식단관리 점수" value="82" unit="점" meta="어제 +4" />
        </div>

        <SectionHeader kicker="REGISTERED" title="등록한 영양제" right={
          <button data-coach="add" onClick={() => go("camera")}
                  style={{ background: "transparent", border: "none",
                          color: "var(--lemon-600)", font: "var(--t-label)",
                          cursor: "pointer" }}>
            + 추가
          </button>
        } />

        {/* Quick-access cards — Camera and Gallery are first-class shortcuts */}
        <div data-coach="quick" style={{ display: "grid",
              gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 4 }}>
          <button onClick={() => go("camera")} style={{
            padding: "16px 14px",
            display: "grid", gap: 6,
            background: "linear-gradient(135deg, #0E0E0E, #1F1A12)",
            border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 18, color: "#fff",
            textAlign: "left", cursor: "pointer",
            boxShadow: "var(--shadow-2)",
          }}>
            <span style={{
              width: 32, height: 32, borderRadius: 10,
              background: "rgba(255,206,0,0.18)",
              color: "var(--lemon-300)",
              display: "grid", placeItems: "center",
            }}>
              <Icon name="camera" size={18} />
            </span>
            <span style={{ font: "700 15px/1.2 var(--font-body)" }}>
              카메라로 촬영
            </span>
            <span style={{ font: "var(--t-caption)", color: "rgba(255,255,255,0.5)",
                            letterSpacing: "0.04em", textTransform: "uppercase" }}>
              Live label · 단일/다중
            </span>
          </button>
          <button onClick={() => go("gallery")} style={{
            padding: "16px 14px",
            display: "grid", gap: 6,
            background: "var(--paper)",
            border: "1px solid var(--ink-100)",
            borderRadius: 18, color: "var(--ink-900)",
            textAlign: "left", cursor: "pointer",
            boxShadow: "var(--shadow-2)",
          }}>
            <span style={{
              width: 32, height: 32, borderRadius: 10,
              background: "var(--lemon-100)",
              color: "var(--lemon-600)",
              display: "grid", placeItems: "center",
            }}>
              <Icon name="images" size={18} />
            </span>
            <span style={{ font: "700 15px/1.2 var(--font-body)" }}>
              갤러리에서 선택
            </span>
            <span style={{ font: "var(--t-caption)", color: "var(--ink-500)",
                            letterSpacing: "0.04em", textTransform: "uppercase" }}>
              앨범 · 즐겨찾기 · 다중 선택
            </span>
          </button>
        </div>

        {DEMO_SUPPLEMENTS.map(s => (
          <div key={s.id} className="lm-row">
            <span style={{
              width: 36, height: 36, borderRadius: 12,
              background: "var(--lemon-100)", color: "var(--lemon-600)",
              display: "grid", placeItems: "center",
            }}>
              <Icon name="pill" />
            </span>
            <div style={{ flex: 1 }}>
              <div style={{ font: "600 15px/1.2 var(--font-body)", color: "var(--ink-900)" }}>
                {s.name}
              </div>
              <div style={{ font: "var(--t-body-sm)", color: "var(--ink-500)", marginTop: 2 }}>
                {s.time} · 성분 {s.count}개
              </div>
            </div>
            <Icon name="chevron-right" color="var(--ink-300)" />
          </div>
        ))}

        <div style={{ marginTop: 20 }}>
          <Disclaimer>
            본 서비스의 정보는 일반적인 건강 관리를 위한 참고 자료입니다.
            의사·약사·영양사의 진단이나 처방을 대체하지 않습니다.
          </Disclaimer>
        </div>
      </div>

      {showCoach && (
        <CoachMarkSequence
          container={rootRef.current}
          onDone={finishCoach}
          steps={[
            { target: '[data-coach="brief"]',
              title: "오늘 한 줄로 시작해요",
              body: "AI Agent가 영양제 · 식단 · 활동량을 함께 보고 가장 중요한 한 가지를 알려드려요.",
              placement: "below" },
            { target: '[data-coach="tiles"]',
              title: "다섯 가지 산출",
              body: "부족 · 과다 · 주의 성분과 식단관리 점수, 그리고 목적별 분석을 한눈에 보여드려요.",
              placement: "below" },
            { target: '[data-coach="add"]',
              title: "사진으로 바로 추가",
              body: "+ 버튼으로 카메라가 열려요. 라벨을 찍거나 갤러리에서 선택하면 분석이 시작돼요.",
              placement: "below" },
          ]}
        />
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// CaptureScreen — router for the photo intake flow:
//   "camera"      — iOS camera viewfinder, single or multi shutter
//   "preview"     — full-bleed photo + retake / use after a single shot
//   "gallery"     — iOS Photos picker grid, single or multi select
//   "analyzing"   — mascot loader with 5-step timeline
//   "ready"       — extracted ingredients preview (→ ReviewScreen)
// ─────────────────────────────────────────────────────────────────
function CaptureScreen({ state, setState, go }) {
  const stage = state.captureStage;

  if (stage === "camera")    return <CameraView    state={state} setState={setState} go={go} />;
  if (stage === "preview")   return <CapturePreview state={state} setState={setState} go={go} />;
  if (stage === "gallery")   return <GalleryView   state={state} setState={setState} go={go} />;
  if (stage === "analyzing") return <AnalyzingView state={state} setState={setState} go={go} />;
  if (stage === "ready")     return <ReadyView     state={state} setState={setState} go={go} />;

  // Fallback — drop the user back into the camera.
  return <CameraView state={state} setState={setState} go={go} />;
}

// ─────────────────────────────────────────────────────────────────
// PermissionSheet — iOS 26 native-style alert. Shows once when
// CameraView mounts and `cameraPermission` is null.
// ─────────────────────────────────────────────────────────────────
function PermissionSheet({ onAllow, onDeny }) {
  return (
    <div className="lm-perm-backdrop">
      <div className="lm-perm-sheet" role="alertdialog">
        <div className="body">
          <div className="icon">
            <img src={lmRes("mLeafComplete", "../../assets/mascot/tablet-frames/03-leaf-complete.png")} alt="" />
          </div>
          <p className="title">"Lemon Aid"이(가) 카메라에 접근하려고 합니다</p>
          <p className="desc">
            영양제 라벨과 식단을 사진으로 분석하기 위해 카메라가 필요해요.
          </p>
          <p className="sub">
            사진은 단말에서 먼저 처리되며, 동의 없이 외부로 전송되지 않아요.
            언제든 설정에서 변경할 수 있습니다.
          </p>
        </div>
        <div className="row">
          <button className="b deny" onClick={onDeny}>허용 안 함</button>
          <span className="sep"></span>
          <button className="b primary" onClick={onAllow}>허용</button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// CameraView — iOS Camera-style viewfinder.
// Top: close / flash / multi-shot toggle.
// Middle: framed "scene" with label-detection guides.
// Bottom: 단일 / 다중 mode, shutter, gallery thumb, flip.
// In 다중 mode a tray of captured frames appears above the action row;
// 확인 button kicks off analysis.
// When `cameraPermission` is unset, a PermissionSheet covers the view.
// ─────────────────────────────────────────────────────────────────
function CameraView({ state, setState, go }) {
  const captures = state.captures || [];
  const multi = state.captureMode === "multi";
  const flash = state.flash || "off";
  const [flashFiring, setFlashFiring] = useStateS(false);
  const permission = state.cameraPermission; // null | 'granted' | 'denied'

  const setMode = m => setState(s => ({ ...s, captureMode: m }));

  const toggleMulti = () => {
    setMode(multi ? "single" : "multi");
    if (multi) setState(s => ({ ...s, captures: [] }));
  };

  const setFlash = () => {
    const next = { off: "on", on: "auto", auto: "off" }[flash];
    setState(s => ({ ...s, flash: next }));
  };

  const fire = () => {
    if (permission !== "granted") return;
    setFlashFiring(true);
    setTimeout(() => setFlashFiring(false), 220);
    const id = `c${Date.now()}`;
    const cap = makeCapture(id, captures.length);
    if (multi) {
      setState(s => ({ ...s, captures: [...(s.captures || []), cap] }));
    } else {
      // Single-shot: stash one capture, surface the preview screen.
      setState(s => ({ ...s, captures: [cap], captureStage: "preview" }));
    }
  };

  const drop = id =>
    setState(s => ({ ...s, captures: (s.captures || []).filter(c => c.id !== id) }));

  const confirmMulti = () => {
    setState(s => ({ ...s, captureStage: "analyzing" }));
    setTimeout(() => setState(s => ({ ...s, captureStage: "ready" })), 2000);
  };

  return (
    <div className="lm-camera">
      {/* viewfinder scene */}
      <div className="viewfinder">
        <div className="scene"><div className="pad"></div></div>
        <div className="guide">
          <span className="guide-corner tl"></span>
          <span className="guide-corner tr"></span>
          <span className="guide-corner bl"></span>
          <span className="guide-corner br"></span>
          <span className="guide-label">Label · 자동 인식 중</span>
        </div>
        <div className="hint">라벨 전체가 사각형 안에 들어오도록 맞춰 주세요</div>
        <div className={`flash-overlay ${flashFiring ? "firing" : ""}`}></div>
      </div>

      {/* top controls — overlay above viewfinder */}
      <header className="top" style={{ position: "absolute", left: 0, right: 0, top: 0 }}>
        <button className="pill" onClick={() => go("home")} aria-label="close">
          <Icon name="x" />
        </button>
        <span className="spacer" />
        <button className={`pill ${flash === "on" ? "flash-on" : ""}`}
                onClick={setFlash} aria-label="flash">
          <Icon name={flash === "off" ? "zap-off" : "zap"} />
        </button>
        <button className={`multi ${multi ? "on" : ""}`} onClick={toggleMulti}>
          <Icon name="layers" size={14} />
          {multi ? `다중 · ${captures.length}장` : "다중 촬영"}
        </button>
      </header>

      {/* multi-shot tray (shown when multi + captures > 0) */}
      {multi && captures.length > 0 && (
        <div className="tray">
          <span className="tray-label">방금 찍은 {captures.length}장</span>
          {captures.map((c, i) => (
            <span key={c.id} className="tray-thumb" title={c.label}>
              {i + 1}
              <span className="x" onClick={(e) => { e.stopPropagation(); drop(c.id); }}>×</span>
            </span>
          ))}
          <button className="confirm" onClick={confirmMulti}>
            <Icon name="check" size={14} strokeWidth={2.2} />
            확인 ({captures.length})
          </button>
        </div>
      )}

      {/* mode selector */}
      <div className="mode-row">
        <span className={`mode ${!multi ? "active" : ""}`} onClick={() => setMode("single")}>단일</span>
        <span className={`mode ${multi  ? "active" : ""}`} onClick={() => setMode("multi")}>다중</span>
      </div>

      {/* action row */}
      <div className="action-row">
        <button className="thumb" onClick={() => setState(s => ({ ...s, captureStage: "gallery" }))}
                 aria-label="open gallery">
          <img src={lmRes("mLeafComplete", "../../assets/mascot/tablet-frames/03-leaf-complete.png")} alt="" />
          {captures.length > 0 && <span className="count">{captures.length}</span>}
        </button>
        <button className={`shutter ${multi ? "multi" : ""}`} onClick={fire} aria-label="capture">
          <span className="inner"></span>
        </button>
        <button className="flip" aria-label="flip camera">
          <Icon name="refresh-cw" size={20} />
        </button>
      </div>

      {/* Permission sheet — overlays everything until granted. */}
      {permission == null && (
        <PermissionSheet
          onAllow={() => setState(s => ({ ...s, cameraPermission: "granted" }))}
          onDeny={() =>  setState(s => ({ ...s, cameraPermission: "denied" }))}
        />
      )}
      {permission === "denied" && (
        <div className="lm-perm-backdrop" style={{ background: "rgba(0,0,0,0.78)" }}>
          <div className="lm-perm-sheet" style={{ width: 280 }}>
            <div className="body">
              <div className="icon" style={{ background: "var(--danger-soft)" }}>
                <Icon name="camera-off" color="var(--danger)" size={28} strokeWidth={1.6} />
              </div>
              <p className="title">카메라 접근이 꺼져 있어요</p>
              <p className="desc">설정 → Lemon Aid에서 카메라를 허용해 주세요. 또는 갤러리에서 라벨 사진을 선택할 수 있어요.</p>
            </div>
            <div className="row">
              <button className="b deny" onClick={() => setState(s => ({ ...s, captureStage: "gallery", cameraPermission: null }))}>갤러리로</button>
              <span className="sep"></span>
              <button className="b primary" onClick={() => setState(s => ({ ...s, cameraPermission: "granted" }))}>설정 열기</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Synthetic "captured photo" record. The CameraView never has access to a
// real camera in this prototype, so we fake the metadata that an iOS app
// would actually attach (timestamp, location, detected label kind).
function makeCapture(id, index) {
  const labels = ["오메가-3 라벨", "비타민 D 라벨", "마그네슘 라벨",
                  "프로바이오틱 라벨", "콜라겐 라벨"];
  const now = new Date();
  const pad = n => String(n).padStart(2, "0");
  return {
    id,
    label: labels[index % labels.length],
    date: `${now.getFullYear()}.${pad(now.getMonth()+1)}.${pad(now.getDate())}`,
    time: `${pad(now.getHours())}:${pad(now.getMinutes())}`,
    loc: "대구 북구 · 자택",
    isLabel: true,
  };
}

// ─────────────────────────────────────────────────────────────────
// CapturePreview — shown after a single-shot, before analysis.
// Full-bleed photo, metadata strip, retake / use buttons.
// ─────────────────────────────────────────────────────────────────
function CapturePreview({ state, setState, go }) {
  const cap = (state.captures || [])[0];
  if (!cap) {
    // Defensive — drop back to camera if state went sideways.
    setState(s => ({ ...s, captureStage: "camera" }));
    return null;
  }
  const startAnalysis = () => {
    setState(s => ({ ...s, captureStage: "analyzing" }));
    setTimeout(() => setState(s => ({ ...s, captureStage: "ready" })), 1800);
  };
  const retake = () => setState(s => ({ ...s, captureStage: "camera", captures: [] }));

  return (
    <div className="lm-preview">
      <header className="top">
        <button className="pill" onClick={retake} aria-label="cancel">
          <Icon name="chevron-left" />
          취소
        </button>
        <span style={{ flex: 1 }} />
        <span className="pill" style={{ background: "rgba(255,255,255,0.10)" }}>
          <Icon name="image" size={14} />
          1장
        </span>
      </header>

      <div className="stage">
        <div className="photo">
          {/* A fake captured "supplement label" — looks like a real photo. */}
          <div className="label-mock">
            <span className="brand">LEMON HEALTH</span>
            <span className="name">멀티비타민 365</span>
            <span className="sub">Multi-Vitamin · 60 tablets · 0.6g</span>
            <span className="stripe"></span>
            <span className="nutri">Vitamin D · 800 IU<br/>Vitamin E · 12 mg α-TE<br/>Omega-3 · 1,000 mg<br/>Zinc · 15 mg</span>
            <span className="stripe" style={{ background: "var(--leaf-400)" }}></span>
          </div>
        </div>
      </div>

      <div className="meta-strip">
        <span className="m"><Icon name="calendar" />{cap.date} {cap.time}</span>
        <span className="m"><Icon name="map-pin" />{cap.loc || "위치 없음"}</span>
        {cap.isLabel && (
          <span className="tag">
            <Icon name="check" size={11} strokeWidth={2.8} />
            라벨 인식 가능
          </span>
        )}
      </div>

      <div className="actions">
        <button className="b retake" onClick={retake}>
          <Icon name="rotate-ccw" size={16} />
          다시 촬영
        </button>
        <button className="b use" onClick={startAnalysis}>
          <Icon name="sparkles" size={16} />
          이 사진으로 분석
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// GalleryView — iOS Photos picker grid with album switcher.
// Toggle 단일 / 다중; numbered badges; bottom CTA pushes count
// into the capture queue and routes to analyzing.
// Selected items show their metadata in a strip under the picker row.
// ─────────────────────────────────────────────────────────────────
function GalleryView({ state, setState, go }) {
  const [selected, setSelected] = useStateS([]);
  const [album, setAlbum] = useStateS(state.album || "recents");
  const [albumOpen, setAlbumOpen] = useStateS(false);
  const multi = state.captureMode === "multi";

  // Apply the album filter — simple in-place rule.
  const filtered = GALLERY_LIBRARY.filter(item => {
    if (album === "all")     return true;
    if (album === "favs")    return !!item.fav;
    if (album === "recents") return true; // demo: all items are "recent"
    if (album === "labels")  return item.album === "labels";
    if (album === "meals")   return item.album === "meals";
    return true;
  });
  const albumDef = ALBUMS.find(a => a.id === album) || ALBUMS[2];

  const toggle = id => {
    if (!multi) {
      setSelected([id]);
      // Single mode: head straight on
      setTimeout(() => commit([id]), 220);
      return;
    }
    setSelected(arr => arr.includes(id) ? arr.filter(x => x !== id) : [...arr, id]);
  };

  const commit = (ids = selected) => {
    if (ids.length === 0) return;
    const map = Object.fromEntries(GALLERY_LIBRARY.map(i => [i.id, i]));
    setState(s => ({
      ...s,
      captures: ids.map((id, i) => {
        const src = map[id] || {};
        return {
          id: `gal-${id}`,
          label: src.label || supplementShotLabel(i),
          date: src.date, time: src.time, loc: src.loc, isLabel: src.isLabel,
        };
      }),
      captureStage: "analyzing",
    }));
    setTimeout(() => setState(s => ({ ...s, captureStage: "ready" })), 1800);
  };

  const back = () => setState(s => ({ ...s, captureStage: "camera" }));

  // Show metadata for the most-recently-selected item.
  const lastSelected = selected.length > 0
    ? GALLERY_LIBRARY.find(i => i.id === selected[selected.length - 1])
    : null;

  return (
    <div className="lm-gallery">
      <header className="top">
        <span className="left" onClick={back}>취소</span>
        <span className="title">사진 선택</span>
        <span className={`right ${selected.length > 0 ? "enabled" : ""}`}
              onClick={() => commit()}>
          {selected.length > 0 ? `추가 (${selected.length})` : "추가"}
        </span>
      </header>

      <div className="source-row">
        <span className="picker" onClick={() => setAlbumOpen(o => !o)}
              style={{ cursor: "pointer" }}>
          {albumDef.name} <Icon name={albumOpen ? "chevron-up" : "chevron-down"} size={14} />
        </span>
        <div className="mode-toggle">
          <span className={`m ${!multi ? "active" : ""}`}
                onClick={() => setState(s => ({ ...s, captureMode: "single" }))}>
            단일
          </span>
          <span className={`m ${multi  ? "active" : ""}`}
                onClick={() => setState(s => ({ ...s, captureMode: "multi" }))}>
            다중
          </span>
        </div>
      </div>

      {/* Selection metadata banner — visible when user has picked something */}
      {lastSelected && (
        <div className="meta-banner">
          <span className="m"><Icon name="calendar" />
            {lastSelected.date} {lastSelected.time}
          </span>
          <span className="m" style={{ minWidth: 0, overflow: "hidden",
                                          textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            <Icon name="map-pin" />
            {lastSelected.loc || "위치 없음"}
          </span>
          {lastSelected.isLabel && (
            <span style={{ marginLeft: "auto",
                            background: "var(--leaf-50)",
                            border: "1px solid var(--leaf-100)",
                            color: "var(--leaf-700)",
                            padding: "3px 8px", borderRadius: 999,
                            font: "700 11px/1 var(--font-body)",
                            display: "inline-flex", gap: 4, alignItems: "center" }}>
              <Icon name="check" size={11} strokeWidth={2.8} />
              라벨
            </span>
          )}
        </div>
      )}

      {/* Album dropdown — appears below the source row */}
      {albumOpen && (
        <div className="lm-album-dropdown">
          {ALBUMS.map(a => {
            const thumb = previewForAlbum(a.id);
            const active = a.id === album;
            return (
              <div key={a.id}
                   className={`opt ${active ? "active" : ""}`}
                   onClick={() => { setAlbum(a.id); setAlbumOpen(false); setSelected([]);
                                    setState(s => ({ ...s, album: a.id })); }}>
                <div className="thumb">{thumb}</div>
                <div className="meta">
                  <span className="name">{a.name}</span>
                  <span className="count">{a.getCount(GALLERY_LIBRARY)}장</span>
                </div>
                <span className="check"><Icon name="check" size={16} strokeWidth={2.4} /></span>
              </div>
            );
          })}
        </div>
      )}

      <div className="grid">
        {filtered.map(item => {
          const idx = selected.indexOf(item.id);
          const isSel = idx !== -1;
          return (
            <div key={item.id}
                 className={`cell ${isSel ? "selected" : ""} ${item.live ? "live" : ""}`}
                 onClick={() => toggle(item.id)}>
              {item.kind === "mascot" ? (
                <img src={item.src} alt={item.label || "mascot"} />
              ) : (
                <div className="placeholder" style={{
                  background: `linear-gradient(135deg, ${item.grad[0]}, ${item.grad[1]})`,
                }}>
                  {item.kind === "label" ? <LabelMockSvg label={item.label} /> : item.label}
                </div>
              )}
              {item.fav && (
                <span className="heart">
                  <Icon name="heart" size={12} strokeWidth={2.4} color="#fff" />
                </span>
              )}
              <span className="badge">{isSel ? (multi ? idx + 1 : "✓") : ""}</span>
            </div>
          );
        })}
      </div>

      <footer className="footer">
        <button className="btn-pri" disabled={selected.length === 0} onClick={() => commit()}>
          <Icon name="sparkles" size={16} />
          {selected.length === 0 ? "사진을 선택해 주세요"
            : multi ? `${selected.length}장 분석 시작` : "분석 시작"}
        </button>
      </footer>
    </div>
  );
}

// Build a thumbnail node for an album option in the dropdown.
function previewForAlbum(id) {
  if (id === "all" || id === "recents") {
    return <img src={lmRes("mIdle", "../../assets/mascot/tablet-frames/00-idle.png")} alt="" />;
  }
  if (id === "favs") {
    return (
      <div style={{ display: "grid", placeItems: "center", height: "100%",
                     background: "linear-gradient(135deg, var(--lemon-300), var(--lemon-500))" }}>
        <Icon name="heart" size={18} color="#fff" strokeWidth={2.2} />
      </div>
    );
  }
  if (id === "labels") {
    return <LabelMockSvg label="라벨" />;
  }
  if (id === "meals") {
    return <div style={{ background: "linear-gradient(135deg, #FFE2AE, #E78A3A)",
                           height: "100%" }} />;
  }
  return null;
}

function supplementShotLabel(i) {
  return ["오메가-3 라벨", "비타민 D 라벨", "마그네슘 라벨",
          "프로바이오틱 라벨", "콜라겐 라벨"][i % 5];
}

// Inline label-style placeholder so the grid feels like real supplement photos.
function LabelMockSvg({ label }) {
  return (
    <svg viewBox="0 0 100 100" width="100%" height="100%" preserveAspectRatio="xMidYMid slice">
      <defs>
        <linearGradient id="bottle" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="rgba(255,255,255,0.45)"/>
          <stop offset="100%" stopColor="rgba(255,255,255,0)"/>
        </linearGradient>
      </defs>
      <rect x="22" y="20" width="56" height="62" rx="6" fill="rgba(255,255,255,0.92)"/>
      <rect x="22" y="20" width="56" height="62" rx="6" fill="url(#bottle)"/>
      <rect x="28" y="30" width="44" height="3" rx="1.5" fill="#1B1300" opacity="0.65"/>
      <rect x="28" y="38" width="34" height="2" rx="1" fill="#1B1300" opacity="0.35"/>
      <rect x="28" y="44" width="40" height="2" rx="1" fill="#1B1300" opacity="0.25"/>
      <text x="50" y="62" textAnchor="middle"
             fill="#1B1300" fontWeight="700" fontSize="9"
             fontFamily="Pretendard, system-ui">
        {label}
      </text>
      <rect x="28" y="68" width="44" height="3" rx="1.5" fill="#FFCE00"/>
      <rect x="28" y="74" width="30" height="2" rx="1" fill="#1B1300" opacity="0.25"/>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────
// AnalyzingView — mascot loader + 5-step timeline.
// ─────────────────────────────────────────────────────────────────
function AnalyzingView({ state, go }) {
  const count = (state.captures || []).length;
  return (
    <div className="lm-screen">
      <AppBar title="라벨 분석" subtitle={`사진 ${count}장 처리 중`}
              onBack={() => null} />
      <div className="lm-scroll">
        <div style={{ marginTop: 28, display: "grid", placeItems: "center", gap: 18 }}>
          <Mascot pose="charged" size={188} />
          <h2 style={{ margin: 0, font: "var(--t-h2)" }}>라벨을 읽고 있어요</h2>
          <p style={{ margin: 0, color: "var(--ink-500)" }}>병원 기록과 함께 살펴보고 있어요.</p>
          <Card style={{ width: "100%", marginTop: 4 }}>
            <Timeline />
          </Card>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// ReadyView — extracted ingredient candidates.
// ─────────────────────────────────────────────────────────────────
function ReadyView({ state, setState, go }) {
  const count = (state.captures || []).length;
  return (
    <div className="lm-screen">
      <AppBar
        title="분석 결과"
        subtitle={`사진 ${count}장 · 4개 성분`}
        onBack={() => setState(s => ({ ...s, captureStage: "camera" }))}
      />
      <div className="lm-scroll">
        <Card glass style={{ marginTop: 12 }}>
          <Pill tone="lemon" icon="check">분석 완료</Pill>
          <h2 style={{ margin: "8px 0 4px", font: "var(--t-h2)" }}>
            4개의 성분을 찾았어요.
          </h2>
          <p style={{ margin: 0, color: "var(--ink-700)" }}>
            저장 전에 항목을 직접 확인해 주세요. 확신도가 낮은 두 항목은
            <b style={{ color: "var(--review)" }}> 확인 필요</b>로 표시했어요.
          </p>
        </Card>
        <SectionHeader title="추출된 성분 4개" />
        <div>
          {DEMO_INGREDIENTS.slice(0, 4).map(i => (
            <IngredientRow
              key={i.id} {...i} checked={i.status !== "review"}
              onToggle={() => {}}
            />
          ))}
        </div>
        <div style={{ marginTop: 20, display: "grid", gap: 8 }}>
          <Button variant="primary" block icon="check"
                   onClick={() => go("review")}>
            저장 전 검토하기
          </Button>
          <Button variant="ghost" block
                   onClick={() => setState(s => ({ ...s, captureStage: "camera", captures: [] }))}>
            다시 촬영
          </Button>
        </div>
      </div>
    </div>
  );
}

function Timeline() {
  const steps = ["Upload", "OCR", "Section", "Structure", "Confirm"];
  const active = 3;
  return (
    <div style={{ display: "grid", gap: 10 }}>
      {steps.map((s, i) => (
        <div key={s} style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{
            width: 22, height: 22, borderRadius: 999,
            background: i < active ? "var(--leaf-600)"
                      : i === active ? "var(--lemon-400)"
                      : "var(--ink-100)",
            color: i <= active ? "white" : "var(--ink-500)",
            display: "grid", placeItems: "center",
            font: "700 11px/1 var(--font-body)",
          }}>
            {i < active ? "✓" : i + 1}
          </span>
          <span style={{
            flex: 1,
            font: "var(--t-label)",
            color: i === active ? "var(--ink-900)" : "var(--ink-500)",
          }}>
            {s}
          </span>
          {i === active && (
            <span style={{ font: "var(--t-caption)", color: "var(--lemon-600)" }}>
              진행 중…
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// ReviewScreen — confirm + register, with low-confidence checkbox UX.
// ─────────────────────────────────────────────────────────────────
function ReviewScreen({ state, setState, go }) {
  const [items, setItems] = useStateS(DEMO_INGREDIENTS.map(i => ({
    ...i, checked: i.status !== "review",
  })));
  const [productName, setProductName] = useStateS("멀티비타민 365");
  const [maker, setMaker] = useStateS("Lemon Health Co.");

  const dupCount = items.filter(i => i.status === "dup" && i.checked).length;
  const reviewCount = items.filter(i => i.status === "review" && i.checked).length;
  const okCount = items.filter(i => i.status === "ok" && i.checked).length;

  return (
    <div className="lm-screen">
      <AppBar
        title="저장 전 확인"
        subtitle="직접 확인한 항목만 저장돼요"
        onBack={() => go("capture")}
      />
      <div className="lm-scroll">
        <SectionHeader title="제품 정보" />
        <div style={{ display: "grid", gap: 8 }}>
          <label className="lm-label" style={{ color: "var(--ink-500)" }}>제품명</label>
          <input className="lm-input" value={productName}
                  onChange={e => setProductName(e.target.value)} />
          <label className="lm-label" style={{ color: "var(--ink-500)", marginTop: 4 }}>
            제조사
          </label>
          <input className="lm-input" value={maker}
                  onChange={e => setMaker(e.target.value)} />
        </div>

        <SectionHeader title="성분 후보 (4개)" right={
          <span style={{ display: "flex", gap: 6 }}>
            <Pill tone="success">{okCount}</Pill>
            <Pill tone="review">{reviewCount}</Pill>
            <Pill tone="warning">{dupCount}</Pill>
          </span>
        } />
        <div>
          {items.map((it, idx) => (
            <IngredientRow
              key={it.id} {...it}
              onToggle={() => setItems(arr => arr.map((x, j) =>
                j === idx ? { ...x, checked: !x.checked } : x))}
            />
          ))}
        </div>

        {reviewCount > 0 && (
          <div style={{ marginTop: 12 }}>
            <Disclaimer tone="lemon" icon="alert-circle">
              <b>확인 필요 항목 포함.</b> 선택한 성분 중 확신도가 낮은 항목이 있어요.
              라벨을 직접 확인한 뒤 저장해 주세요.
            </Disclaimer>
          </div>
        )}

        <SectionHeader title="복용 일정" />
        <div className="lm-row" style={{ flexWrap: "wrap", gap: 8 }}>
          {["아침", "점심", "저녁", "취침 전"].map(t => (
            <span key={t} className={`lm-chip ${t === "아침" ? "active" : ""}`}>
              {t}
            </span>
          ))}
        </div>

        <div style={{ marginTop: 20 }}>
          <Disclaimer>
            본 서비스의 정보는 일반적인 건강 관리를 위한 참고 자료입니다.
            복용 변경은 의사·약사와 상담하세요.
          </Disclaimer>
        </div>
      </div>
      <div style={{ position: "absolute", left: 16, right: 16, bottom: 56,
                    display: "grid", gap: 8, zIndex: 6 }}>
        <Button variant="success" block icon="check"
                 onClick={() => { setState(s => ({ ...s, captureStage: "camera", captures: [] })); go("home"); }}>
          확인 후 저장
        </Button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// ChatScreen — the agent chat surface.
// ─────────────────────────────────────────────────────────────────
function ChatScreen({ go }) {
  const messages = [
    { from: "agent",
      body: <>안녕하세요. 도움이 되는, 당신의 레몬에이드예요. 오늘은 어떤 도움이 필요하세요?</> },
    { from: "user",
      body: <>오늘 점심에 비타민 D를 더 먹어도 될까요?</> },
    { from: "agent",
      body: <>현재 등록한 영양제 두 종에서 비타민 D가 함께 들어 있어요.
              하루 합계가 권장량의 92%여서 추가는 신중히 결정해 주세요.
              자세한 상담은 약사님께 권해 드려요.</> },
    { from: "user",
      body: <>그럼 식단으로 보충하는 방법은요?</> },
  ];
  return (
    <div className="lm-screen">
      <AppBar
        title="레몬에이드 Agent"
        subtitle="병원 기록을 기억하는 동반자"
        right={
          <span style={{ display: "flex", alignItems: "center", gap: 6,
                          font: "var(--t-caption)", color: "var(--leaf-600)" }}>
            <span style={{ width: 8, height: 8, borderRadius: 999,
                            background: "var(--leaf-500)" }} />
            온라인
          </span>
        }
      />
      <div className="lm-scroll" style={{ paddingTop: 16, display: "flex",
                                            flexDirection: "column", gap: 8 }}>
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 4 }}>
          <Pill tone="info" icon="info">AI는 거드는 손길 · 진단 아님</Pill>
        </div>
        {messages.map((m, i) => <Bubble key={i} from={m.from}>{m.body}</Bubble>)}
        <div style={{ display: "flex", alignItems: "flex-end", gap: 6, alignSelf: "flex-start" }}>
          <Mascot pose="thinking" size={36} style={{ filter: "none" }} />
          <Bubble from="agent">
            <span style={{ display: "inline-flex", gap: 3 }}>
              <Dot delay={0} />
              <Dot delay={150} />
              <Dot delay={300} />
            </span>
          </Bubble>
        </div>
      </div>

      <div style={{
        position: "absolute", left: 16, right: 16, bottom: 110,
        display: "flex", gap: 8, alignItems: "center",
        padding: 6, paddingLeft: 14,
        background: "var(--paper)",
        border: "1px solid var(--ink-100)",
        borderRadius: 999,
        boxShadow: "var(--shadow-2)",
        zIndex: 6,
      }}>
        <Icon name="paperclip" color="var(--ink-500)" />
        <input
          placeholder="레몬에이드에게 질문해 보세요"
          style={{ flex: 1, border: "none", outline: "none", background: "transparent",
                   font: "var(--t-body)", color: "var(--ink-900)" }}
        />
        <button style={{
          width: 36, height: 36, borderRadius: 999, border: "none",
          background: "var(--lemon-400)", display: "grid", placeItems: "center",
          cursor: "pointer", color: "var(--ink-900)",
        }} aria-label="send">
          <Icon name="arrow-up" strokeWidth={2.2} />
        </button>
      </div>
    </div>
  );
}

function Dot({ delay }) {
  return (
    <span style={{
      width: 6, height: 6, borderRadius: 999, background: "var(--ink-300)",
      animation: `lm-rise 1.2s ease-in-out infinite`,
      animationDelay: `${delay}ms`,
    }} />
  );
}

// ─────────────────────────────────────────────────────────────────
// ConsentScreen — re-entry view of granted consents (Settings).
// ─────────────────────────────────────────────────────────────────
function ConsentScreen({ state, setState, go }) {
  const toggle = key => setState(s => ({
    ...s, consents: { ...s.consents, [key]: !s.consents[key] },
  }));
  return (
    <div className="lm-screen">
      <AppBar title="동의 설정" subtitle="언제든 변경할 수 있어요" />
      <div className="lm-scroll">
        <SectionHeader kicker="REQUIRED" title="필수 동의" />
        <ConsentRow
          label="라벨 이미지 OCR 처리"
          sub="기본값: 외부 전송 비활성. 분석은 단말과 안전한 서버에서만."
          granted={state.consents.ocr}
          onToggle={() => toggle("ocr")}
        />
        <div style={{ height: 8 }} />
        <ConsentRow
          label="민감 건강정보 분석"
          sub="만성질환·검사값 컨텍스트를 안전하게 결합합니다."
          granted={state.consents.health}
          onToggle={() => toggle("health")}
        />
        <SectionHeader kicker="OPTIONAL" title="선택 동의" />
        <ConsentRow
          label="HealthKit / Health Connect 연동"
          sub="걸음수·심박수·체중 데이터를 자동으로 가져옵니다."
          granted={!!state.consents.health_connect}
          onToggle={() => toggle("health_connect")}
        />
        <div style={{ height: 8 }} />
        <ConsentRow
          label="학습 데이터 저장"
          sub="제품 미스매치 사례만 익명화하여 OCR 정확도 개선에 사용합니다."
          granted={!!state.consents.learning}
          onToggle={() => toggle("learning")}
        />
        <div style={{ marginTop: 20 }}>
          <Disclaimer tone="danger" icon="shield-alert">
            <b>처방전·검사표는 사용자 확인이 끝난 뒤에만 저장됩니다.</b>
            본 앱은 복용 변경이나 진단을 직접 안내하지 않습니다.
          </Disclaimer>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, {
  OnboardingScreen, DashboardScreen, CaptureScreen, ReviewScreen,
  ChatScreen, ConsentScreen, Timeline, Toggle,
  CameraView, GalleryView, AnalyzingView, ReadyView, LabelMockSvg,
  PermissionSheet, CapturePreview,
});
