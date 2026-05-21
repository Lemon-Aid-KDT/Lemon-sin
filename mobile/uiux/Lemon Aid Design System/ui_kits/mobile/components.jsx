// components.jsx — Lemon Aid mobile UI kit primitives.
// All components are scoped with the `lm-` CSS classes from mobile-kit.css.
// Exports go onto window so other <script type="text/babel"> files can use them.
//
// Notes for editors:
//  - Inline `style={{}}` is used for layout that varies per-instance.
//  - Class names from mobile-kit.css carry the visual language.
//  - Lucide icons are loaded via the CDN in index.html and rendered through
//    the <Icon name="..." /> helper below, which lets us keep the icon nodes
//    in the JSX tree (vs lucide.createIcons() scanning the DOM).

const { useState, useEffect, useRef, createElement } = React;

// Resource resolver — when bundled into a standalone HTML, mascot URLs are
// inlined and exposed as `window.__resources[id]`. In dev mode the lookup
// falls through to the original relative path, so editing locally still works.
function lmRes(id, fallback) {
  const r = (typeof window !== "undefined" && window.__resources) || {};
  return r[id] || fallback;
}

// Debounced global call: all Icon mounts within a frame coalesce into one
// lucide.createIcons() sweep. Without this, dozens of useEffects each
// running createIcons() makes the page sluggish.
let __lucideQueued = false;
function __queueLucide() {
  if (__lucideQueued) return;
  __lucideQueued = true;
  requestAnimationFrame(() => {
    __lucideQueued = false;
    if (window.lucide && window.lucide.createIcons) {
      try { window.lucide.createIcons(); } catch (e) {}
    }
  });
}

// ─────────────────────────────────────────────────────────────────
// Icon — thin wrapper around <i data-lucide="…">. Calls lucide.createIcons()
// after mount so the SVG appears whether or not the host page calls it.
// ─────────────────────────────────────────────────────────────────
function Icon({ name, size = 18, color, strokeWidth = 1.85, style = {} }) {
  useEffect(__queueLucide, [name]);
  return (
    <i
      data-lucide={name}
      style={{
        display: "inline-flex",
        alignItems: "center",
        color: color || "currentColor",
        width: size, height: size,
        flexShrink: 0,
        strokeWidth,
        ...style,
      }}
    />
  );
}

// Re-scan the DOM after each render and let Lucide swap data-lucide
// attributes for inline SVG. createIcons() is idempotent and cheap.
function useLucide() {
  useEffect(() => {
    if (window.lucide && window.lucide.createIcons) {
      window.lucide.createIcons();
    }
  });
}

// ─────────────────────────────────────────────────────────────────
// AppBar — sticky frosted header with optional back / actions.
// ─────────────────────────────────────────────────────────────────
function AppBar({ title, subtitle, onBack, right }) {
  return (
    <header className="lm-appbar">
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {onBack && (
          <button
            onClick={onBack}
            aria-label="back"
            style={{
              padding: 6, marginLeft: -6, background: "transparent",
              border: "none", color: "var(--ink-700)", cursor: "pointer",
            }}
          >
            <Icon name="chevron-left" />
          </button>
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <h1 style={{
            margin: 0, font: "var(--t-h3)", color: "var(--ink-900)",
            letterSpacing: "-0.005em", whiteSpace: "nowrap",
            overflow: "hidden", textOverflow: "ellipsis",
          }}>{title}</h1>
          {subtitle && (
            <div style={{ font: "var(--t-caption)", color: "var(--ink-500)" }}>
              {subtitle}
            </div>
          )}
        </div>
        {right}
      </div>
    </header>
  );
}

// ─────────────────────────────────────────────────────────────────
// BottomTabs — 5-tab capsule with a centre "+" FAB.
// vision · chatbot · (+) · community · menu
// The + button is handled by the parent (opens a palette sheet).
// ─────────────────────────────────────────────────────────────────
function BottomTabs({ value, onChange, onPlus }) {
  const left = [
    { id: "vision",    label: "비전",    icon: "scan-line" },
    { id: "chatbot",   label: "챗봇",    icon: "message-circle" },
  ];
  const right = [
    { id: "community", label: "커뮤니티", icon: "users" },
    { id: "menu",      label: "목록",    icon: "menu" },
  ];
  return (
    <nav className="lm-tabbar" role="tablist">
      {left.map(t => (
        <button key={t.id}
                className={`lm-tab ${value === t.id ? "active" : ""}`}
                onClick={() => onChange(t.id)}>
          <Icon name={t.icon} />
          {t.label}
        </button>
      ))}
      <button className={`lm-tab plus ${value === "plus" ? "active" : ""}`}
              onClick={() => onPlus && onPlus()}
              aria-label="quick add">
        <Icon name="plus" strokeWidth={2.6} />
      </button>
      {right.map(t => (
        <button key={t.id}
                className={`lm-tab ${value === t.id ? "active" : ""}`}
                onClick={() => onChange(t.id)}>
          <Icon name={t.icon} />
          {t.label}
        </button>
      ))}
    </nav>
  );
}

// ─────────────────────────────────────────────────────────────────
// Card primitives.
// ─────────────────────────────────────────────────────────────────
function Card({ glass, children, style, onClick }) {
  return (
    <div
      className={`lm-card ${glass ? "glass" : ""}`}
      style={style}
      onClick={onClick}
    >
      {children}
    </div>
  );
}

function Tile({ icon, iconBg, iconColor, label, value, unit, meta, onClick }) {
  return (
    <div className="lm-tile" onClick={onClick}>
      <div className="head">
        <span className="ico" style={{
          background: iconBg || "var(--lemon-100)",
          color: iconColor || "var(--lemon-600)",
        }}>
          <Icon name={icon} size={16} />
        </span>
        <span className="meta">{label}</span>
      </div>
      <div className="num">
        {value}{unit && <span className="u">{unit}</span>}
      </div>
      {meta && <div style={{ font: "var(--t-body-sm)", color: "var(--ink-500)" }}>{meta}</div>}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// Button & Pill
// ─────────────────────────────────────────────────────────────────
function Button({ variant = "primary", icon, block, onClick, disabled, children, style }) {
  return (
    <button
      className={`lm-btn ${variant} ${block ? "block" : ""}`}
      onClick={onClick}
      disabled={disabled}
      style={style}
    >
      {icon && <Icon name={icon} />}
      {children}
    </button>
  );
}

function Pill({ tone = "info", icon, children, style }) {
  return (
    <span className={`lm-pill ${tone}`} style={style}>
      {icon && <Icon name={icon} size={12} />}
      {children}
    </span>
  );
}

// ─────────────────────────────────────────────────────────────────
// Disclaimer — every recommendation surface ends with one of these.
// ─────────────────────────────────────────────────────────────────
function Disclaimer({ tone = "info", icon = "info", children }) {
  return (
    <div className={`lm-disclaimer ${tone === "info" ? "" : tone}`}>
      <span style={{ marginTop: 1 }}><Icon name={icon} size={18} /></span>
      <div>{children}</div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// IngredientRow — a single ingredient candidate.
// ─────────────────────────────────────────────────────────────────
function IngredientRow({ name, amount, unit, confidence, status, onToggle, checked }) {
  const pillTone = status === "ok" ? "success"
                  : status === "review" ? "review"
                  : status === "dup" ? "warning"
                  : "info";
  const pillIcon = status === "ok" ? "check"
                  : status === "review" ? "alert-circle"
                  : status === "dup" ? "alert-triangle"
                  : "info";
  const pillLabel = status === "ok" ? "충분"
                   : status === "review" ? "확인 필요"
                   : status === "dup" ? "다른 영양제와 겹침"
                   : status;
  return (
    <div className="lm-row" onClick={onToggle} style={{ cursor: "pointer" }}>
      <span style={{
        width: 22, height: 22, borderRadius: 7,
        border: `1.6px solid ${checked ? "var(--lemon-400)" : "var(--ink-200)"}`,
        background: checked ? "var(--lemon-400)" : "transparent",
        display: "grid", placeItems: "center",
        color: "var(--ink-900)",
      }}>
        {checked && <Icon name="check" size={14} strokeWidth={3} />}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ font: "600 15px/1.2 var(--font-body)", color: "var(--ink-900)" }}>
          {name}
        </div>
        <div style={{ font: "var(--t-body-sm)", color: "var(--ink-500)", marginTop: 2 }}>
          {amount} {unit} · 확신도 {Math.round(confidence * 100)}%
        </div>
      </div>
      <Pill tone={pillTone} icon={pillIcon}>{pillLabel}</Pill>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// Mascot — three poses pulled from /assets/mascot/.
// ─────────────────────────────────────────────────────────────────
function Mascot({ pose = "idle", size = 96, style = {} }) {
  const src = {
    idle:        lmRes("mLeafComplete", "../../assets/mascot/tablet-frames/03-leaf-complete.png"),
    thinking:    lmRes("mCarbonating",  "../../assets/mascot/tablet-frames/01-carbonating.png"),
    charged:     lmRes("mCharged",      "../../assets/mascot/tablet-frames/02-charged.png"),
    complete:    lmRes("mLeafComplete", "../../assets/mascot/tablet-frames/03-leaf-complete.png"),
    empty:       lmRes("mEmptyShell",   "../../assets/mascot/frames/00-empty-shell.png"),
    rising:      lmRes("mMidRising",    "../../assets/mascot/frames/01-mid-rising.png"),
    leaf:        lmRes("mLeafGrowth",   "../../assets/mascot/frames/02-leaf-growth.png"),
    reference:   lmRes("mCutout",       "../../assets/mascot/character-cutout.png"),
  }[pose] || lmRes("mIdle", "../../assets/mascot/tablet-frames/00-idle.png");

  return (
    <img
      src={src}
      alt="Lemon Aid"
      className="lm-loader-mascot"
      style={{
        width: size, height: size, objectFit: "contain",
        filter: "drop-shadow(0 10px 14px rgba(214,158,0,0.30))",
        ...style,
      }}
    />
  );
}

// ─────────────────────────────────────────────────────────────────
// Wordmark — the only place Lemon-Aid is rendered with brand colours.
// ─────────────────────────────────────────────────────────────────
function Wordmark({ size = 32 }) {
  return (
    <span style={{
      font: `800 ${size}px/1 var(--font-display)`,
      letterSpacing: "-0.02em",
    }}>
      <span style={{ color: "var(--lemon-500)" }}>Lemon</span>
      <span style={{ color: "var(--ink-300)" }}>-</span>
      <span style={{ color: "var(--leaf-500)" }}>Aid</span>
    </span>
  );
}

// ─────────────────────────────────────────────────────────────────
// Bubble — chat bubble.
// ─────────────────────────────────────────────────────────────────
function Bubble({ from, children }) {
  return <div className={`lm-bubble ${from}`}>{children}</div>;
}

// ─────────────────────────────────────────────────────────────────
// Section header (small caps, tight padding).
// ─────────────────────────────────────────────────────────────────
function SectionHeader({ kicker, title, right }) {
  return (
    <div style={{
      display: "flex", alignItems: "baseline", gap: 8,
      padding: "20px 4px 10px",
    }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        {kicker && (
          <div style={{
            font: "var(--t-caption)", color: "var(--ink-500)",
            letterSpacing: "0.06em", textTransform: "uppercase",
          }}>{kicker}</div>
        )}
        <h2 style={{ margin: 0, font: "var(--t-h3)", color: "var(--ink-900)" }}>
          {title}
        </h2>
      </div>
      {right}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// ProgressBar — top of each onboarding step.
// ─────────────────────────────────────────────────────────────────
function ProgressBar({ value, max = 1 }) {
  const pct = Math.max(0, Math.min(1, value / max)) * 100;
  return (
    <div className="progress" role="progressbar"
         aria-valuenow={value} aria-valuemax={max}>
      <div className="fill" style={{ width: `${pct}%` }}></div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// BottomSheet — slide-up modal for pickers (gender, purpose, time).
// Caller controls open/close. Click backdrop to dismiss.
// ─────────────────────────────────────────────────────────────────
function BottomSheet({ open, title, desc, onClose, children }) {
  if (!open) return null;
  return (
    <div className="lm-sheet-backdrop" onClick={onClose}>
      <div className="lm-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="handle"></div>
        {title && <h2 className="title">{title}</h2>}
        {desc && <p className="desc">{desc}</p>}
        {children}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// RulerPicker — horizontal ruler with tick marks; tap arrows to nudge.
// Pillyze uses a scroll-and-snap behavior; we fake the scroll via
// React state + a transform on the tick row.
// ─────────────────────────────────────────────────────────────────
function RulerPicker({ value, unit, min, max, step = 0.1, hint, onChange }) {
  const range = max - min;
  // 0..1 position of the current value within the range.
  const t = (value - min) / range;
  // We render ~31 ticks visible around the cursor.
  const total = Math.round(range / step);
  const tickWidth = 8; // 2px + 6px gap
  // Center the active tick under the fixed cursor at 50% by translating row.
  const offset = -(t * total * tickWidth);
  const displayValue = Number.isInteger(step) ? Math.round(value) : value.toFixed(1);

  const nudge = (delta) => {
    const next = Math.max(min, Math.min(max, +(value + delta).toFixed(1)));
    onChange && onChange(next);
  };

  return (
    <div className="lm-ruler">
      <div className="value" onWheel={(e) => nudge(-Math.sign(e.deltaY) * step)}>
        {displayValue}
        {unit && <span className="unit">{unit}</span>}
      </div>
      <div className="ticks">
        <div className="row" style={{ left: "50%", transform: `translateX(${offset}px)` }}>
          {Array.from({ length: total + 1 }, (_, i) => {
            const isMajor = i % 10 === 0;
            const isLabel = i % 50 === 0;
            const tickVal = min + i * step;
            return (
              <span
                key={i}
                className={`t ${isMajor ? "major" : ""} ${isLabel ? "label" : ""}`}
                data-label={isLabel ? Math.round(tickVal) : undefined}
                style={isLabel ? { position: "relative" } : undefined}
              />
            );
          })}
        </div>
        <div className="cursor"></div>
      </div>
      {hint && <div className="hint">{hint}</div>}
      <div style={{ display: "flex", gap: 8, justifyContent: "center", marginTop: 10 }}>
        <button onClick={() => nudge(-step)}
                style={btnNudgeStyle}>−</button>
        <button onClick={() => nudge(+step)}
                style={btnNudgeStyle}>+</button>
      </div>
    </div>
  );
}
const btnNudgeStyle = {
  width: 40, height: 32, borderRadius: 12,
  background: "var(--canvas)", border: "1px solid var(--ink-200)",
  color: "var(--ink-700)", font: "700 18px/1 var(--font-body)",
  cursor: "pointer",
};

// ─────────────────────────────────────────────────────────────────
// ConcernCard — single tile inside the health-concern grid.
// ─────────────────────────────────────────────────────────────────
function ConcernCard({ icon, label, badge, selected, onClick, gradient }) {
  return (
    <div className={`lm-concern-card ${selected ? "selected" : ""}`} onClick={onClick}>
      {badge && <span className="badge">{badge}</span>}
      <span className="check"><Icon name="check" size={12} strokeWidth={3} /></span>
      <span className="ico-3d" style={{ background: gradient }}>
        <Icon name={icon} size={28} strokeWidth={1.8} color="#fff" />
      </span>
      <div className="label">{label}</div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// Cube — single tile inside the customizable dashboard grid.
// ─────────────────────────────────────────────────────────────────
function Cube({ label, value, unit, sub, progress, valueTone, full, onRemove }) {
  const cls = "lm-cube" + (full ? " full" : "");
  return (
    <div className={cls} style={full ? { gridColumn: "1 / -1" } : undefined}>
      {onRemove && <span className="ko" onClick={onRemove}>−</span>}
      <span className="corner"><Icon name="grip-vertical" size={14} /></span>
      <div className="label">{label}</div>
      <div className={`value ${valueTone || ""}`}>
        {value}{unit && <span className="unit">{unit}</span>}
      </div>
      {typeof progress === "number" && (
        <div className="bar"><div className="fill" style={{ width: `${progress}%` }} /></div>
      )}
      {sub && <div className="sub">{sub}</div>}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// CoachMark — translucent dark overlay + bottom tooltip with pointer.
// ─────────────────────────────────────────────────────────────────
function CoachMark({ title, body, bottom = 90 }) {
  return (
    <>
      <div className="lm-coach-backdrop"></div>
      <div className="lm-coach-tip" style={{ left: 16, right: 16, bottom }}>
        <p className="h">{title}</p>
        <p className="b">{body}</p>
        <div className="point">
          <Icon name="hand-pointing-down" size={22} />
        </div>
      </div>
    </>
  );
}

// ─────────────────────────────────────────────────────────────────
// Dots — page indicator used on welcome carousel.
// ─────────────────────────────────────────────────────────────────
function Dots({ count, active }) {
  return (
    <div className="lm-dots">
      {Array.from({ length: count }, (_, i) => (
        <span key={i} className={`d ${i === active ? "active" : ""}`}></span>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// Carousel — auto-advancing, swipe-enabled slider.
// Children become the slides; one child = one page.
// ─────────────────────────────────────────────────────────────────
function Carousel({ value, onChange, interval = 4500, children }) {
  const slides = React.Children.toArray(children);
  const count = slides.length;
  const [drag, setDrag] = useState(null); // { startX, dx }
  const ref = useRef(null);
  const wrap = (n) => ((n % count) + count) % count;

  // Auto-advance unless the user is actively dragging.
  // Pause it when interval is 0 or when there's only one slide.
  const valRef = useRef(value);
  valRef.current = value;
  useEffect(() => {
    if (drag || count < 2 || !interval || interval < 100) return undefined;
    const tick = () => {
      try { onChange(((valRef.current + 1) % count + count) % count); }
      catch (e) {}
    };
    const t = setInterval(tick, interval);
    return () => clearInterval(t);
  }, [drag, interval, count, onChange]);

  const onStart = (e) => {
    const x = e.touches ? e.touches[0].clientX : e.clientX;
    setDrag({ startX: x, dx: 0 });
  };
  const onMove = (e) => {
    if (!drag) return;
    const x = e.touches ? e.touches[0].clientX : e.clientX;
    setDrag({ ...drag, dx: x - drag.startX });
  };
  const onEnd = () => {
    if (!drag) return;
    const w = ref.current ? ref.current.offsetWidth : 320;
    const ratio = drag.dx / w;
    if (ratio < -0.18) onChange(wrap(value + 1));
    else if (ratio > 0.18) onChange(wrap(value - 1));
    setDrag(null);
  };

  const trackStyle = {
    transform: `translateX(calc(${-value * 100}% + ${drag ? drag.dx : 0}px))`,
  };
  return (
    <div className="lm-carousel" ref={ref}
         onMouseDown={onStart} onMouseMove={onMove}
         onMouseUp={onEnd}     onMouseLeave={onEnd}
         onTouchStart={onStart} onTouchMove={onMove} onTouchEnd={onEnd}>
      <div className={`track ${drag ? "dragging" : ""}`} style={trackStyle}>
        {slides.map((s, i) => (
          <div key={i} className="slide">{s}</div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// NumericKeypad — iOS-style 3×4 keypad. Calls onKey('0'..'9' | 'back' | 'done').
// ─────────────────────────────────────────────────────────────────
function NumericKeypad({ onKey, withLetters = true }) {
  const keys = [
    { d: "1", l: "" },
    { d: "2", l: "ABC" },
    { d: "3", l: "DEF" },
    { d: "4", l: "GHI" },
    { d: "5", l: "JKL" },
    { d: "6", l: "MNO" },
    { d: "7", l: "PQRS" },
    { d: "8", l: "TUV" },
    { d: "9", l: "WXYZ" },
  ];
  return (
    <div className="lm-keypad">
      {keys.map(k => (
        <span key={k.d} className="key" onClick={() => onKey(k.d)}>
          <span className="digit">{k.d}</span>
          {withLetters && k.l && <span className="letters">{k.l}</span>}
        </span>
      ))}
      <span className="key blank"></span>
      <span className="key" onClick={() => onKey("0")}>
        <span className="digit">0</span>
      </span>
      <span className="key backspace" onClick={() => onKey("back")}
            aria-label="backspace">
        <svg width="22" height="16" viewBox="0 0 22 16" fill="none"
             stroke="#000" strokeWidth="1.6">
          <path d="M6 1H19a2 2 0 012 2v10a2 2 0 01-2 2H6L1 8l5-7z"/>
          <path d="M10 5l6 6M16 5l-6 6" strokeLinecap="round"/>
        </svg>
      </span>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// WheelPicker — iOS-style scrolling wheel with N columns.
// columns = [{ id, items: [string], value, onChange }]
// ─────────────────────────────────────────────────────────────────
function WheelPicker({ columns }) {
  return (
    <div className="lm-wheel">
      <div className="selection"></div>
      {columns.map((col) => (
        <WheelColumn key={col.id} {...col} />
      ))}
    </div>
  );
}

function WheelColumn({ items, value, onChange }) {
  const ref = useRef(null);
  const ITEM = 32;

  // Scroll into position whenever value changes from outside.
  useEffect(() => {
    if (!ref.current) return;
    const idx = items.indexOf(value);
    if (idx >= 0) ref.current.scrollTop = idx * ITEM;
  }, [value, items]);

  const onScroll = () => {
    if (!ref.current) return;
    const idx = Math.round(ref.current.scrollTop / ITEM);
    const clamped = Math.max(0, Math.min(items.length - 1, idx));
    const next = items[clamped];
    if (next !== value) onChange && onChange(next);
  };

  const activeIdx = items.indexOf(value);
  return (
    <div className="col" ref={ref} onScroll={onScroll}>
      <div className="pad"></div>
      {items.map((item, i) => (
        <div key={i} className={`item ${i === activeIdx ? "center" : ""}`}>
          {item}
        </div>
      ))}
      <div className="pad"></div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// ReorderList — pointer-based drag-reorder.
// `items` is an array of objects with `.id`; `onReorder(newArray)` fires
// after release. `renderItem(item, isDragging)` returns the card.
// ─────────────────────────────────────────────────────────────────
function ReorderList({ items, onReorder, renderItem, handleSelector = ".corner" }) {
  const [dragging, setDragging] = useState(null);  // id
  const [insertIdx, setInsertIdx] = useState(null); // where line shows
  const rectsRef = useRef([]);
  const startRef = useRef(0);

  const onPointerDown = (e, id, idx) => {
    // Only start drag if the pointerdown hit the handle.
    const handle = e.target.closest(handleSelector);
    if (!handle) return;
    e.preventDefault();
    e.currentTarget.setPointerCapture && e.currentTarget.setPointerCapture(e.pointerId);
    // Snapshot every item's rect at drag start.
    rectsRef.current = Array.from(e.currentTarget.parentElement.children)
      .filter(c => c.classList.contains("item"))
      .map(c => c.getBoundingClientRect());
    startRef.current = e.clientY;
    setDragging(id);
    setInsertIdx(idx);
  };

  const onPointerMove = (e) => {
    if (!dragging) return;
    const y = e.clientY;
    const rects = rectsRef.current;
    let next = rects.length;
    for (let i = 0; i < rects.length; i++) {
      const mid = rects[i].top + rects[i].height / 2;
      if (y < mid) { next = i; break; }
    }
    setInsertIdx(next);
  };

  const onPointerUp = () => {
    if (!dragging) return;
    const fromIdx = items.findIndex(i => i.id === dragging);
    let toIdx = insertIdx;
    if (toIdx > fromIdx) toIdx -= 1;
    if (toIdx !== fromIdx && toIdx >= 0 && toIdx <= items.length - 1) {
      const next = [...items];
      const [m] = next.splice(fromIdx, 1);
      next.splice(toIdx, 0, m);
      onReorder(next);
    }
    setDragging(null);
    setInsertIdx(null);
    rectsRef.current = [];
  };

  return (
    <div className="lm-reorder" onPointerMove={onPointerMove} onPointerUp={onPointerUp}
         onPointerCancel={onPointerUp}>
      {items.map((it, i) => (
        <div key={it.id}
             className={`item ${dragging === it.id ? "dragging" : ""}`}
             onPointerDown={(e) => onPointerDown(e, it.id, i)}>
          {renderItem(it, dragging === it.id)}
        </div>
      ))}
      {dragging && insertIdx != null && rectsRef.current.length > 0 && (() => {
        // Position the insert line at the boundary between items.
        const rects = rectsRef.current;
        let top;
        if (insertIdx === 0) top = rects[0].top;
        else if (insertIdx >= rects.length) top = rects[rects.length - 1].bottom;
        else top = (rects[insertIdx - 1].bottom + rects[insertIdx].top) / 2;
        const containerTop = rects[0].top;
        return (
          <div className="insert-line" style={{ top: top - containerTop - 1 }}></div>
        );
      })()}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// CoachMarkSequence — full-screen step-by-step walkthrough.
// steps: [{ target: selector | rectFn, title, body, placement: 'below'|'above' }]
// ─────────────────────────────────────────────────────────────────
function CoachMarkSequence({ steps, onDone, container }) {
  const [i, setI] = useState(0);
  const [rect, setRect] = useState(null);
  const [tipTop, setTipTop] = useState(120);

  const step = steps[i];

  useEffect(() => {
    if (!step) return;
    const compute = () => {
      const root = container || document.body;
      const rootRect = root.getBoundingClientRect();
      const el = typeof step.target === "string"
        ? root.querySelector(step.target)
        : step.target && step.target();
      if (!el) { setRect(null); return; }
      const r = el.getBoundingClientRect();
      const local = {
        x: r.left - rootRect.left,
        y: r.top - rootRect.top,
        w: r.width, h: r.height,
      };
      setRect(local);
      const placement = step.placement || (local.y > rootRect.height / 2 ? "above" : "below");
      const tipH = 150;
      setTipTop(placement === "above"
        ? Math.max(60, local.y - tipH - 14)
        : Math.min(rootRect.height - tipH - 12, local.y + local.h + 14));
    };
    compute();
    // Recompute after a beat to handle async layout.
    const t = setTimeout(compute, 80);
    return () => clearTimeout(t);
  }, [i, step, container]);

  if (!step) return null;
  const last = i === steps.length - 1;

  return (
    <div className="lm-coach-seq">
      <div className="scrim" onClick={onDone}></div>
      {rect ? (
        <div className="spotlight" style={{
          left: rect.x - 6, top: rect.y - 6,
          width: rect.w + 12, height: rect.h + 12,
        }}></div>
      ) : (
        // Fallback: dim the screen but no spotlight.
        <div className="scrim" style={{ background: "rgba(8,6,0,0.62)" }}></div>
      )}
      <div className="tip" style={{ left: 16, right: 16, top: tipTop }}>
        <div className={`arrow ${rect && tipTop < rect.y ? "bottom" : "top"}`}
             style={rect ? {
               left: Math.max(20, Math.min(280, rect.x + rect.w / 2 - 32)),
             } : undefined}></div>
        <h3>{step.title}</h3>
        <p>{step.body}</p>
        <div className="row">
          <button className="skip" onClick={onDone}>건너뛰기</button>
          <span className="progress">{i + 1} / {steps.length}</span>
          <button className="next"
                  onClick={() => (last ? onDone() : setI(i + 1))}>
            {last ? "시작하기" : "다음"}
          </button>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, {
  Icon, useLucide, AppBar, BottomTabs, Card, Tile, Button, Pill, Disclaimer,
  IngredientRow, Mascot, Wordmark, Bubble, SectionHeader,
  ProgressBar, BottomSheet, RulerPicker, ConcernCard, Cube, CoachMark, Dots,
  Carousel, NumericKeypad, WheelPicker, WheelColumn, ReorderList, CoachMarkSequence,
});
