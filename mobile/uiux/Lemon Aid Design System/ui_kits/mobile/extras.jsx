// extras.jsx — VisionLanding, PaletteSheet, HamburgerDrawer, Community, MenuList.
// All depend on globals from components.jsx / screens.jsx.

const { useState: useStateX } = React;

// ─────────────────────────────────────────────────────────────────
// VisionLanding — entry point for the unified 비전 tab.
// Two large CTAs: 사진찍기 / 갤러리에서 선택.
// ─────────────────────────────────────────────────────────────────
function VisionLanding({ state, setState, go }) {
  // The Vision tab's two CTAs go to the camera or gallery sub-stages of the
  // capture route. We use `go(...)` so the route actually changes — just
  // mutating `captureStage` doesn't navigate.
  const start = (target) => go(target); // "camera" | "gallery"

  return (
    <div className="lm-screen">
      <AppBar title="비전" subtitle="사진으로 분석을 시작해 보세요" />
      <div className="lm-scroll">
        <div style={{ display: "grid", placeItems: "center", padding: "20px 0 16px" }}>
          <Mascot pose="charged" size={160} />
        </div>

        <h2 style={{ margin: "4px 0 6px",
                      font: "800 24px/1.25 var(--font-display)",
                      letterSpacing: "-0.01em" }}>
          영양제 라벨 · 식단 사진을<br/>한 번에 분석해 드릴게요.
        </h2>
        <p style={{ margin: 0, color: "var(--ink-500)", font: "var(--t-body)" }}>
          어떤 방식으로 시작할까요? 둘 중 편한 쪽을 선택하세요.
        </p>

        <div style={{ marginTop: 20, display: "grid", gap: 12 }}>
          <button onClick={() => start("camera")} style={{
            display: "grid", gap: 8, padding: "20px 18px",
            background: "linear-gradient(135deg, #0E0E0E, #1F1A12)",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 20, color: "#fff",
            textAlign: "left", cursor: "pointer",
            boxShadow: "var(--shadow-3)",
          }}>
            <span style={{
              width: 42, height: 42, borderRadius: 14,
              background: "rgba(255,206,0,0.18)",
              color: "var(--lemon-300)",
              display: "grid", placeItems: "center",
            }}>
              <Icon name="camera" size={22} />
            </span>
            <span style={{ font: "800 18px/1.2 var(--font-body)" }}>사진찍기</span>
            <span style={{ font: "var(--t-body-sm)", color: "rgba(255,255,255,0.6)" }}>
              실시간 라벨 인식 가이드와 단일·다중 촬영 지원
            </span>
            <span style={{ alignSelf: "flex-end", marginTop: -28,
                            color: "var(--lemon-300)" }}>
              <Icon name="arrow-right" size={20} />
            </span>
          </button>

          <button onClick={() => start("gallery")} style={{
            display: "grid", gap: 8, padding: "20px 18px",
            background: "var(--paper)",
            border: "1px solid var(--ink-100)",
            borderRadius: 20, color: "var(--ink-900)",
            textAlign: "left", cursor: "pointer",
            boxShadow: "var(--shadow-2)",
          }}>
            <span style={{
              width: 42, height: 42, borderRadius: 14,
              background: "var(--lemon-100)",
              color: "var(--lemon-600)",
              display: "grid", placeItems: "center",
            }}>
              <Icon name="images" size={22} />
            </span>
            <span style={{ font: "800 18px/1.2 var(--font-body)" }}>갤러리에서 선택</span>
            <span style={{ font: "var(--t-body-sm)", color: "var(--ink-500)" }}>
              앨범 전환 · 즐겨찾기 · 한 번에 여러 장 선택
            </span>
            <span style={{ alignSelf: "flex-end", marginTop: -28,
                            color: "var(--lemon-600)" }}>
              <Icon name="arrow-right" size={20} />
            </span>
          </button>
        </div>

        <div style={{ marginTop: 20 }}>
          <Disclaimer tone="lemon" icon="sparkles">
            <b>AI는 거드는 손길이에요.</b> 분석 결과는 저장 전에 다시 보여드릴게요. 직접 확인한 항목만 저장됩니다.
          </Disclaimer>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// PaletteSheet — the bottom-sheet that opens when the centre + is tapped.
// Five quick-action shortcuts arranged in a colourful palette.
// ─────────────────────────────────────────────────────────────────
function PaletteSheet({ open, onClose, go }) {
  if (!open) return null;
  const items = [
    { id: "home",    label: "홈 대시보드",  icon: "layout-dashboard",
      grad: "linear-gradient(135deg, var(--lemon-200), var(--lemon-500))" },
    { id: "suppdb",  label: "영양제 DB",   icon: "pill",
      grad: "linear-gradient(135deg, #E0D4FF, #9981E8)" },
    { id: "fooddb",  label: "음식 DB",     icon: "utensils",
      grad: "linear-gradient(135deg, #FFE2AE, #E78A3A)" },
    { id: "consent", label: "사용자 설정",  icon: "settings-2",
      grad: "linear-gradient(135deg, #C8E7FF, #4FA9F0)" },
    { id: "menu",    label: "목록",        icon: "list",
      grad: "linear-gradient(135deg, #D7F3DC, #6FCB73)" },
  ];
  return (
    <div className="lm-sheet-backdrop" onClick={onClose}>
      <div className="lm-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="handle"></div>
        <h2 className="title">빠른 이동</h2>
        <p className="desc">팔레트에서 가고 싶은 곳을 골라 주세요.</p>
        <div style={{
          display: "grid", gridTemplateColumns: "repeat(3, 1fr)",
          gap: 10, marginBottom: 8,
        }}>
          {items.map(it => (
            <button key={it.id} onClick={() => { onClose(); go(it.id); }}
                    style={{
              padding: "14px 8px 10px",
              border: "1px solid var(--ink-100)",
              background: "var(--paper)",
              borderRadius: 16, cursor: "pointer",
              display: "grid", gap: 6, justifyItems: "center",
              textAlign: "center",
            }}>
              <span style={{
                width: 44, height: 44, borderRadius: 14,
                background: it.grad,
                color: "#fff",
                display: "grid", placeItems: "center",
                boxShadow: "var(--shadow-1)",
              }}>
                <Icon name={it.icon} size={22} strokeWidth={2} color="#fff" />
              </span>
              <span style={{ font: "600 12px/1.3 var(--font-body)",
                              color: "var(--ink-900)" }}>{it.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// HamburgerDrawer — slides in from the right, lists every feature.
// ─────────────────────────────────────────────────────────────────
function HamburgerDrawer({ open, onClose, go }) {
  if (!open) return null;
  const sections = [
    { label: "분석", items: [
      { id: "vision",   icon: "scan-line",       name: "비전 (라벨 · 식단)" },
      { id: "review",   icon: "check-circle",    name: "라벨 검토 결과" },
      { id: "chatbot",  icon: "message-circle",  name: "AI 챗봇 대화" },
    ]},
    { label: "기록", items: [
      { id: "home",      icon: "layout-dashboard", name: "오늘 대시보드" },
      { id: "community", icon: "users",            name: "커뮤니티" },
      { id: "suppdb",    icon: "pill",             name: "영양제 데이터베이스" },
      { id: "fooddb",    icon: "utensils",         name: "음식 데이터베이스" },
    ]},
    { label: "계정", items: [
      { id: "onboarding", icon: "user",          name: "프로필 다시 설정" },
      { id: "consent",    icon: "shield-check",  name: "동의 · 개인정보" },
      { id: "help",       icon: "life-buoy",     name: "고객 지원" },
    ]},
  ];
  return (
    <div style={{
      position: "absolute", inset: 0, zIndex: 50,
      background: "rgba(0,0,0,0.45)",
    }} onClick={onClose}>
      <aside style={{
        position: "absolute", top: 0, right: 0, bottom: 0,
        width: "84%", maxWidth: 340,
        background: var_paper_solid(),
        boxShadow: "-18px 0 36px rgba(27,19,0,0.25)",
        display: "flex", flexDirection: "column",
        overflow: "hidden",
        animation: "lm-slide-in-r 280ms cubic-bezier(0.32,0.72,0,1) both",
      }} onClick={(e) => e.stopPropagation()}>
        <header style={{ padding: "56px 18px 12px",
                         background: "var(--canvas)",
                         display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{
            width: 44, height: 44, borderRadius: 14,
            background: "linear-gradient(135deg, var(--lemon-300), var(--lemon-500))",
            display: "grid", placeItems: "center",
            font: "900 16px/1 var(--font-display)", color: "var(--ink-900)",
          }}>박</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ font: "700 16px/1.2 var(--font-body)" }}>박준영님</div>
            <div style={{ font: "var(--t-caption)", color: "var(--ink-500)",
                            letterSpacing: "0.04em", textTransform: "uppercase" }}>
              영양제 섭취 관리 · 30대
            </div>
          </div>
          <button onClick={onClose} aria-label="close"
                  style={{ width: 32, height: 32, borderRadius: 999,
                           border: "none", background: "var(--ink-100)",
                           color: "var(--ink-700)", display: "grid",
                           placeItems: "center", cursor: "pointer" }}>
            <Icon name="x" />
          </button>
        </header>
        <div style={{ flex: 1, overflowY: "auto", padding: "8px 0 80px",
                       background: "var(--paper)" }}>
          {sections.map(sec => (
            <div key={sec.label}>
              <div style={{
                font: "var(--t-caption)", color: "var(--ink-500)",
                letterSpacing: "0.06em", textTransform: "uppercase",
                padding: "18px 18px 8px",
              }}>{sec.label}</div>
              {sec.items.map(it => (
                <button key={it.id} onClick={() => { onClose(); go(it.id); }}
                        style={{
                  width: "100%", display: "flex", alignItems: "center", gap: 12,
                  padding: "12px 18px",
                  background: "transparent", border: "none",
                  cursor: "pointer", textAlign: "left",
                  color: "var(--ink-900)",
                }}>
                  <span style={{
                    width: 32, height: 32, borderRadius: 10,
                    background: "var(--canvas)", color: "var(--lemon-600)",
                    display: "grid", placeItems: "center",
                  }}>
                    <Icon name={it.icon} size={16} />
                  </span>
                  <span style={{ flex: 1, font: "600 14px/1.2 var(--font-body)" }}>
                    {it.name}
                  </span>
                  <Icon name="chevron-right" size={14} color="var(--ink-300)" />
                </button>
              ))}
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
}
function var_paper_solid() {
  return "var(--paper)";
}

// ─────────────────────────────────────────────────────────────────
// CommunityScreen — placeholder community feed.
// ─────────────────────────────────────────────────────────────────
function CommunityScreen({ go }) {
  const posts = [
    { id: "p1", author: "민지", time: "방금 전",
      title: "비타민 D는 아침에 먹는 게 좋을까요?",
      tag: "비타민 D", likes: 24, comments: 8 },
    { id: "p2", author: "성훈", time: "1시간 전",
      title: "고혈압 약과 오메가-3 함께 복용 후기",
      tag: "오메가-3", likes: 42, comments: 16 },
    { id: "p3", author: "지윤", time: "오늘 09:12",
      title: "당뇨 식단으로 1주일 — 식단관리 점수 변화",
      tag: "식단", likes: 81, comments: 22 },
  ];
  return (
    <div className="lm-screen">
      <AppBar title="커뮤니티" subtitle="같은 고민, 같은 경험" />
      <div className="lm-scroll">
        <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
          {["전체", "만성질환", "영양제", "식단", "운동"].map((t, i) => (
            <span key={t} className={`lm-chip ${i === 0 ? "active" : ""}`}>{t}</span>
          ))}
        </div>
        {posts.map(p => (
          <div key={p.id} className="lm-row" style={{ display: "grid", gap: 6,
                                                        alignItems: "stretch" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{
                width: 28, height: 28, borderRadius: 999,
                background: "linear-gradient(135deg, var(--lemon-200), var(--lemon-500))",
                color: "var(--ink-900)",
                display: "grid", placeItems: "center",
                font: "700 12px/1 var(--font-body)",
              }}>{p.author[0]}</span>
              <span style={{ font: "600 13px/1.2 var(--font-body)" }}>{p.author}</span>
              <span style={{ font: "var(--t-caption)", color: "var(--ink-500)" }}>· {p.time}</span>
              <span className="lm-pill lemon" style={{ marginLeft: "auto" }}>{p.tag}</span>
            </div>
            <div style={{ font: "700 15px/1.3 var(--font-body)" }}>{p.title}</div>
            <div style={{ display: "flex", gap: 14, color: "var(--ink-500)",
                            font: "var(--t-body-sm)" }}>
              <span style={{ display: "inline-flex", gap: 4, alignItems: "center" }}>
                <Icon name="heart" size={14} /> {p.likes}
              </span>
              <span style={{ display: "inline-flex", gap: 4, alignItems: "center" }}>
                <Icon name="message-square" size={14} /> {p.comments}
              </span>
            </div>
          </div>
        ))}
        <div style={{ marginTop: 16 }}>
          <Disclaimer>
            본 커뮤니티의 의견은 일반적인 경험 공유이며, 의료 자문이 아닙니다. 복용 변경은 의사·약사와 상담하세요.
          </Disclaimer>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// MenuListScreen — full feature index as a long scroll.
// (Mirror of the hamburger drawer; useful as a destination page.)
// ─────────────────────────────────────────────────────────────────
function MenuListScreen({ go }) {
  const groups = [
    { label: "분석 도구", color: "var(--lemon-100)", icon: "var(--lemon-600)", items: [
      { id: "vision",   icon: "scan-line",      name: "비전",        sub: "사진으로 라벨 분석" },
      { id: "chatbot",  icon: "message-circle", name: "AI 챗봇",      sub: "건강 질문 상담" },
      { id: "review",   icon: "check-circle",   name: "라벨 검토",    sub: "저장 전 확인" },
    ]},
    { label: "데이터베이스", color: "#E0D4FF", icon: "#5F47C7", items: [
      { id: "suppdb",   icon: "pill",     name: "영양제 DB",  sub: "성분 검색 · 권장량" },
      { id: "fooddb",   icon: "utensils", name: "음식 DB",    sub: "한국 음식 영양 정보" },
    ]},
    { label: "기록 · 커뮤니티", color: "var(--leaf-100)", icon: "var(--leaf-700)", items: [
      { id: "home",      icon: "layout-dashboard", name: "오늘 대시보드", sub: "다섯 가지 산출" },
      { id: "community", icon: "users",            name: "커뮤니티",      sub: "같은 고민의 사람들" },
    ]},
    { label: "계정", color: "#FFEACC", icon: "#7A4200", items: [
      { id: "onboarding", icon: "user",          name: "프로필",      sub: "정보 다시 설정" },
      { id: "consent",    icon: "shield-check",  name: "동의 설정",    sub: "개인정보 · 알림" },
    ]},
  ];
  return (
    <div className="lm-screen">
      <AppBar title="목록" subtitle="모든 기능을 한눈에" />
      <div className="lm-scroll">
        {groups.map(g => (
          <React.Fragment key={g.label}>
            <SectionHeader kicker={g.label} title="" />
            {g.items.map(it => (
              <div key={it.id} className="lm-row"
                    onClick={() => go(it.id)} style={{ cursor: "pointer" }}>
                <span style={{
                  width: 38, height: 38, borderRadius: 12,
                  background: g.color, color: g.icon,
                  display: "grid", placeItems: "center",
                }}>
                  <Icon name={it.icon} />
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ font: "600 15px/1.2 var(--font-body)" }}>{it.name}</div>
                  <div style={{ font: "var(--t-body-sm)", color: "var(--ink-500)",
                                  marginTop: 2 }}>{it.sub}</div>
                </div>
                <Icon name="chevron-right" color="var(--ink-300)" />
              </div>
            ))}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// SupplementDB / FoodDB — placeholder DB browsers.
// ─────────────────────────────────────────────────────────────────
function SupplementDBScreen() {
  const items = [
    { id: "vd",   name: "비타민 D",     unit: "IU", rec: "800–1,000",
      tag: "지용성", color: "var(--lemon-100)", ico: "var(--lemon-600)" },
    { id: "ome",  name: "오메가-3",     unit: "mg", rec: "1,000–2,000",
      tag: "EPA+DHA", color: "var(--info-soft)", ico: "var(--info)" },
    { id: "mg",   name: "마그네슘",     unit: "mg", rec: "320–420",
      tag: "미네랄", color: "var(--leaf-50)", ico: "var(--leaf-600)" },
    { id: "zn",   name: "아연",         unit: "mg", rec: "8–11",
      tag: "미네랄", color: "var(--review-soft)", ico: "var(--review)" },
    { id: "vc",   name: "비타민 C",     unit: "mg", rec: "75–100",
      tag: "수용성", color: "var(--warning-soft)", ico: "#7A4200" },
  ];
  return (
    <div className="lm-screen">
      <AppBar title="영양제 DB" subtitle="성분 · 권장 섭취량 (KDRIs 2025)" />
      <div className="lm-scroll">
        <div className="lm-row" style={{ padding: "10px 14px" }}>
          <Icon name="search" color="var(--ink-500)" />
          <input placeholder="성분명 · 제품명 검색"
                 style={{ flex: 1, border: "none", outline: "none",
                          background: "transparent", font: "var(--t-body)",
                          color: "var(--ink-900)" }} />
        </div>
        {items.map(it => (
          <div key={it.id} className="lm-row">
            <span style={{ width: 38, height: 38, borderRadius: 12,
                            background: it.color, color: it.ico,
                            display: "grid", placeItems: "center" }}>
              <Icon name="pill" />
            </span>
            <div style={{ flex: 1 }}>
              <div style={{ font: "600 15px/1.2 var(--font-body)" }}>{it.name}</div>
              <div style={{ font: "var(--t-body-sm)", color: "var(--ink-500)" }}>
                권장 {it.rec} {it.unit} · {it.tag}
              </div>
            </div>
            <span className="lm-pill success">KDRIs</span>
          </div>
        ))}
        <Disclaimer>
          KDRIs 2025 기준입니다. 만성질환·연령에 따라 권장량이 달라질 수 있어요.
        </Disclaimer>
      </div>
    </div>
  );
}

function FoodDBScreen() {
  const items = [
    { id: "chicken", name: "닭가슴살", kcal: 165, protein: 31, fat: 3.6,
      img: "linear-gradient(135deg,#FFE2AE,#E78A3A)" },
    { id: "rice",    name: "현미밥",   kcal: 218, protein: 4.5, fat: 1.7,
      img: "linear-gradient(135deg,#F4E6BE,#C49443)" },
    { id: "salmon",  name: "구운 연어", kcal: 232, protein: 25, fat: 14,
      img: "linear-gradient(135deg,#FFD3B0,#D86A2A)" },
    { id: "tofu",    name: "두부",     kcal: 76,  protein: 8,   fat: 4.8,
      img: "linear-gradient(135deg,#FFF4D8,#C0AB6B)" },
    { id: "banana",  name: "바나나",   kcal: 89,  protein: 1.1, fat: 0.3,
      img: "linear-gradient(135deg,#FFF5C7,#E0B017)" },
  ];
  return (
    <div className="lm-screen">
      <AppBar title="음식 DB" subtitle="한국 표준 식품성분표 기반" />
      <div className="lm-scroll">
        <div className="lm-row" style={{ padding: "10px 14px" }}>
          <Icon name="search" color="var(--ink-500)" />
          <input placeholder="음식 이름 검색"
                 style={{ flex: 1, border: "none", outline: "none",
                          background: "transparent", font: "var(--t-body)" }} />
        </div>
        {items.map(it => (
          <div key={it.id} className="lm-row">
            <span style={{ width: 44, height: 44, borderRadius: 14,
                            background: it.img,
                            display: "grid", placeItems: "center",
                            color: "#fff" }}>
              <Icon name="utensils" />
            </span>
            <div style={{ flex: 1 }}>
              <div style={{ font: "600 15px/1.2 var(--font-body)" }}>{it.name}</div>
              <div style={{ font: "var(--t-body-sm)", color: "var(--ink-500)" }}>
                100g · {it.kcal} kcal · 단백 {it.protein}g · 지방 {it.fat}g
              </div>
            </div>
            <Icon name="chevron-right" color="var(--ink-300)" />
          </div>
        ))}
        <Disclaimer>
          농촌진흥청 국가표준식품성분표 기준 100g 영양 정보입니다.
        </Disclaimer>
      </div>
    </div>
  );
}

Object.assign(window, {
  VisionLanding, PaletteSheet, HamburgerDrawer,
  CommunityScreen, MenuListScreen, SupplementDBScreen, FoodDBScreen,
});
