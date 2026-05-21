# Lemon Aid Design System

> **Lemon Aid (레몬에이드)** — *"도움이 되는, 당신의 레몬에이드"* — an AI-powered
> chronic-disease companion. One photo of a supplement label or a meal, and
> the agent reads it alongside the user's hospital records, prescriptions and
> activity data to surface five outputs: missing nutrients, over-intake,
> watch-out ingredients, a meal-management score, and a purpose-based brief.
>
> The brand is built around a single 3D glass lemon mascot, an Apple-style
> liquid-glass surface language, and explicit "helping hand — never
> prescriber" tone.

This is the design system folder. It contains the colors, type, fonts, brand
assets, components and screen recreations that any agent (or human designer)
needs to make on-brand artefacts for Lemon Aid — production code, throwaway
prototypes, slides, marketing pieces, anything.

---

## 1. Product & Company Context

| Field | Value |
|---|---|
| Product | **Lemon Aid** (레몬에이드) mobile companion app |
| Parent / client | **(주)레몬헬스케어** — operator of the LDB clinical data exchange (claims-처리 770만+, 80% of Korean tertiary hospitals) |
| Team | 경북대학교 AI / 빅데이터 전문가 양성 과정 — Lemon Aid team |
| Pivot | From *청구의신* (insurance claims, sunset 2025) → *건강의신* (B2C health management) |
| Audience | Korean adults with chronic conditions juggling 3–5 supplements + prescriptions + diet |
| Platforms | iOS 26, iPadOS 26, macOS 26 (App Store presence on each), Flutter mobile app today |

### Three messages, repeated everywhere

1. **사진 한 장으로 끝.** — One photo. Five outputs.
2. **병원 기록을 기억하는 Agent.** — The agent remembers chronic conditions, meds and labs.
3. **AI는 거드는 손길.** — AI helps. The user decides. Previews before approval, never diagnosis.

### Five outputs the app must always produce

- 부족 영양소 — *missing nutrients vs. KDRIs 2025*
- 과다 섭취 — *over-intake based on overlap across supplements*
- 주의 성분 — *interactions, medication or condition watch-outs*
- 식단관리 점수 — *meal-management score*
- 목적별 분석 — *goal-based brief (weight, energy, fatigue management)*

### Sources used to build this design system

- **Local codebase** (mounted): `03_lemon_healthcare/yeong-Lemon-Aid/`
  - `mobile/flutter_app/lib/` — Flutter app structure, screens, theme seed `Color(0xFF4E8F73)` (leaf green)
  - `mobile/CLAUDE.md` — official Material 3 palette + spacing scale + disclaimer copy
  - `assets/mascot/…` — character design bundle, gold variant, Lottie carbon-leaf-growth animations
  - `docs/`, `docs/Nutrition-docs/`, `docs/Integration-docs/` — product intent, compliance, tone rules
- **GitHub repositories** (read-only access for downstream agents):
  - [`Lemon-Aid-KDT/Lemon-sin`](https://github.com/Lemon-Aid-KDT/Lemon-sin) (branch `yeong-tech`) — primary working tree
  - [`HorangEe02/Project_yeong`](https://github.com/HorangEe02/Project_yeong) (branch `main`, subtree `03_lemon_healthcare/`) — personal mirror, identical content
- **Brand reference**: Apple iOS 26 / iPadOS 26 / macOS 26, https://www.apple.com/kr/ — for liquid-glass surfaces and App Store presence layout.
- **Provided fonts**: `에이투지체` (AtoZ) — Thin / ExtraBold / Black weights. Used as the *display* family.

> **For downstream agents:** if you have access, browse the GitHub repos above
> for richer context. `docs/Nutrition-docs/` has fifty+ design-rationale
> documents covering algorithms, compliance, OCR pipelines and KDRIs lookup —
> all useful when wording UI text or designing flows.

---

## 2. File index

```
.
├── README.md                       ← you are here
├── SKILL.md                        ← portable agent skill manifest
├── colors_and_type.css             ← token source of truth (CSS custom props)
├── fonts/
│   └── AtoZ-{1Thin,8ExtraBold,9Black}.ttf
├── assets/
│   └── mascot/
│       ├── character-cutout.png    ← transparent hero mascot
│       ├── character-original.png  ← full reference sheet (poses + usage)
│       ├── gold-poster.png         ← warm gold variant
│       ├── frames/                 ← carbon-rising loader keyframes
│       ├── gold-frames/            ← gold loader keyframes
│       └── tablet-frames/          ← agent-thinking loader keyframes
├── preview/                        ← Design System tab cards (HTML)
│   ├── wordmark.html
│   ├── palette-brand.html
│   ├── palette-neutrals.html
│   ├── palette-semantic.html
│   ├── type-display.html
│   ├── type-body.html
│   ├── type-numerals.html
│   ├── radii.html
│   ├── spacing.html
│   ├── shadows-glass.html
│   ├── mascot-poses.html
│   ├── mascot-loader.html
│   ├── icons.html
│   ├── component-buttons.html
│   ├── component-fields.html
│   ├── component-cards.html
│   ├── component-badges.html
│   ├── component-nav.html
│   └── component-disclaimer.html
└── ui_kits/
    └── mobile/                     ← iOS 26 liquid-glass mobile UI kit
        ├── README.md
        ├── index.html              ← interactive click-thru prototype
        ├── App.jsx
        ├── theme.jsx               ← maps colors_and_type.css → JS
        └── components/             ← one file per primitive
```

---

## 3. Visual Foundations

### 3.1 Color

| Role | Token | Hex |
|---|---|---|
| Primary — lemon core | `--lemon-400` | `#FFCE00` |
| Primary container — pale lemon | `--lemon-100` | `#FFF8C7` |
| Secondary — leaf gloss | `--leaf-300` | `#6FCB73` |
| Success — deep leaf | `--leaf-600` | `#1F8A4A` |
| Trust accent — sky | `--sky-400` | `#4FC3F7` |
| Warning | — | `#FB8C00` |
| Review ("확인 필요") | `--review` | `#B86A00` |
| Danger | — | `#D9342B` |
| Text — warm near-black | `--ink-900` | `#1B1300` |
| Body text | `--ink-700` | `#3C3526` |
| Canvas / paper | `--canvas` / `--paper` | `#FBF8EC` / `#FFFDF6` |

**Rationale.** The Flutter theme seeds Material 3 from leaf green
`Color(0xFF4E8F73)`, while `mobile/CLAUDE.md` codifies a brighter lemon yellow
as primary. Both are correct — lemon for *brand surfaces and the wordmark*,
leaf for *seeded UI generation and success / growth states.* The dashboard's
review states use an amber `--review`, distinct from system warning orange.

Backgrounds are **always warm**: `--canvas` (`#FBF8EC`) or `--paper`
(`#FFFDF6`). Pure white is for tiny areas only (numeric displays inside
glass). Never use cool greys.

### 3.2 Type

- **Display (`--font-display`)** — `AtoZ` (provided), weights 100 / 800 / 900.
  Use for the wordmark, hero numbers and section headers ≥ 34 px. AtoZ is a
  geometric Korean display face; it sets the playful liquid-glass mood
  without going cute.
- **Body (`--font-body`)** — `Pretendard Variable` via jsDelivr CDN, falling
  back to Apple SD Gothic Neo → Noto Sans KR. Pretendard is the de-facto
  Korean product font and matches the Flutter app's `google_fonts` reach for
  Noto Sans KR.
- **Mono** — system `SF Mono` / `JetBrains Mono` / `Roboto Mono`. Used for
  ingredient codes, OCR debug text and KDRIs IDs.

**Scale** (cribbed from iOS 26 large-title cadence): 56 / 44 / 34 / 26 / 20 /
17 / 15 / 13 / 11. The big numbers in dashboard cards are 56 px display,
tabular numerals, `letter-spacing: -0.02em`.

> 🚩 **Font substitution flag.** AtoZ ships in 3 weights only (Thin /
> ExtraBold / Black). The brand brief expects intermediate weights for
> headings — for now, we use AtoZ ExtraBold (800) for display headings and
> Pretendard 600 / 700 for h2–h4. If a designer has the full AtoZ family,
> drop the additional `.ttf` files into `/fonts/` and add `@font-face`
> entries to `colors_and_type.css`.

### 3.3 Backgrounds, surfaces & liquid glass

- The default page background is `--canvas`, a creamy warm white.
- Cards are `--paper` with `--shadow-2` and a 1-px `--ink-100` hairline
  border — never a coloured border-left accent (an AI-slop trope we
  explicitly avoid).
- **Liquid-glass cards** layer `backdrop-filter: blur(20px) saturate(140%)` on
  a translucent `rgba(255,255,255,0.55)` fill, with an inner highlight ring
  (`--glass-inner-hl`) and the warm `--glass-shadow` drop. Use for hero
  numbers, the dashboard summary, and any overlay sheet (modals, photo
  capture).
- No bluish-purple gradients. No emoji cards. No coloured left borders.

### 3.4 Corner radii & shape

- App-level surfaces (sheets, hero cards): `--r-2xl` (36 px).
- Cards / panels: `--r-lg` (20 px).
- Inputs, badges, chips: `--r-md` (14 px) or `--r-pill` for capsules.
- Tiny tags and code: `--r-xs` (6 px).

The character itself is round; the system follows.

### 3.5 Spacing

4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 56. Section spacing on mobile
defaults to 24; inside cards 16.

### 3.6 Shadow & elevation

- `--shadow-1` for hairlines / sticky chrome.
- `--shadow-2` for resting cards.
- `--shadow-3` for raised sheets (modals, image previews).
- `--shadow-lemon` for the active primary CTA — a warm yellow halo.

The dashboard tiles wear `--shadow-2` at rest and lift to `--shadow-3` on
press with a 2-px translate. No animated lift on hover (mobile-first
product).

### 3.7 Borders & hairlines

- 1 px `--ink-100` for card stroke.
- 1 px `--ink-200` divider between rows.
- 2 px `--lemon-400` focus ring on inputs.

### 3.8 Animation

- Easing: a single `cubic-bezier(0.32, 0.72, 0, 1)` ("liquid glass" — taken
  from iOS large-title behaviour). Duration: 240 ms for taps, 360 ms for
  sheets.
- Loaders use the *carbon-rising-then-leaf-grows* Lottie sequence
  (`assets/mascot/tablet-frames/`). Never use spinners on the dashboard.
- Hover state on web previews: `opacity 0.92`, *not* darker colour.
- Press state: `transform: scale(0.97)` for buttons; tiles dip 2 px with a
  shadow swap.
- Page transitions: cross-fade + 4-px lift for incoming sheets.

### 3.9 Transparency & blur

- Used in liquid-glass cards, the bottom tab bar, the camera capture sheet
  and the AI-typing chat surface.
- Never on text-heavy detail panels (legibility wins).

### 3.10 Imagery vibe

- Photos that appear in the product (supplement labels, meals) keep their
  natural colour temperature but sit on `--canvas` with a 4-px white inner
  ring to feel "lifted".
- The mascot and gold-poster art are warm-yellow biased; pair them only with
  the lemon / leaf palette, never with the sky blue.

### 3.11 Layout rules

- Mobile: 16-px page padding, 8-pt grid.
- App headers are sticky with a 80 %-translucent paper fill and a
  `backdrop-filter: blur(24px)`.
- Bottom navigation is a floating liquid-glass capsule with a 28-px corner
  radius and 12-px inset from screen edges (iOS 26 pattern).

---

## 4. Content Fundamentals — how Lemon Aid speaks

### Voice in one line

> *Cheerful, plain-spoken, and unmistakably non-diagnostic.* Lemon Aid is a
> companion that hands the user information and asks them to decide.

### Tone rules

- **Korean first.** All user-facing copy is Korean, formal but warm
  (`~합니다 / ~합시다 / ~해보세요`). English appears only for ingredient
  symbols (e.g. `Vitamin D`, `Omega-3`) and developer-mode labels.
- **You-form is `당신` or implicit subject.** No `너`. We don't gender.
- **No emoji in product UI.** The brand brief explicitly forbids system
  emoji; we use custom liquid-glass SVGs (lemon, leaf, drop) for the rare
  case a glyph is needed. Marketing pages may use the mascot.
- **Verbs > adjectives.** "사진으로 등록할게요" beats "쉽고 빠른 등록".
- **Numbers are loud, units are quiet.** `120 mg` — number is `--t-num-xl`,
  unit is `--t-label` in `--ink-500`.
- **Sentence case for English, no shouting.** Buttons read "Start analysis"
  not "START ANALYSIS".

### Casing & punctuation

| Surface | Rule | Example |
|---|---|---|
| Title (Korean) | No trailing punctuation | `오늘의 영양 상태` |
| Body (Korean) | Period (`.`) ends declarative sentences | `오늘 단백질이 부족해요.` |
| Button (Korean) | Verb-final, no period | `사진으로 분석하기` |
| Title (English) | Sentence case | `Today's nutrient balance` |
| Button (English) | Imperative, no period | `Start analysis` |
| Numbers | Tabular numerals, comma separators | `1,250 kcal` |

### Compliance copy — never break these

Lifted verbatim from `docs/10-compliance-checklist.md`:

| Avoid (진단 / 처방 / 치료) | Prefer (건강관리 보조) |
|---|---|
| "당뇨 진단 결과" | "혈당 관리 권고" |
| "이 영양제를 처방드립니다" | "비타민 D 섭취량을 늘리는 것을 고려해보세요" |
| "약을 중단하세요" | "복용 변경은 의사·약사와 상담하세요" |
| "이 음식이 피로를 치료해요" | "이 음식은 피로 관리와 관련된 영양 섭취를 도울 수 있어요" |

### Standard disclaimer block (use the `<MedicalDisclaimer>` component)

> *본 서비스에서 제공하는 정보는 일반적인 건강 관리를 위한 참고 자료이며, 의사·약사·영양사의 전문적 진단이나 처방을 대체하지 않습니다.*

Every recommendation screen (nutrition, weight prediction, exercise,
purpose) must end with this block. PRs missing it are rejected.

### Specific phrasing samples

- Empty state on dashboard: `아직 분석 데이터가 없어요. 영양제나 식단을 등록해 보세요.`
- OCR low confidence: `라벨을 직접 확인해 주세요. 일부 항목은 확신도가 낮아요.`
- Agent intro line: `안녕하세요. 도움이 되는, 당신의 레몬에이드예요.`
- Approval-before-action: `사진을 분석해도 될까요? 결과는 저장 전에 다시 보여드릴게요.`

---

## 5. Iconography

### Approach

The brand brief is unambiguous: **no system emoji**. Apple-style liquid-glass
SVGs are the icon language, created bespoke for the brand. For everything
else we use a single CDN-backed icon set with a consistent stroke weight, so
the bespoke glyphs and the workhorse glyphs read as one family.

### Bespoke icons (in `assets/mascot/` and inside `preview/icons.html`)

The mascot's character-design sheet defines three **brand glyphs** — each
rendered in the same liquid-glass style as the mascot:

| Glyph | Concept | Use |
|---|---|---|
| 🍋 lemon slice | 도움 (Help — "substantive help") | Primary brand bullet, hero illustrations |
| 🌿 leaf | 성장 (Growth — "partner walking with you") | Success states, the leaf cap on the mascot |
| 💧 drop | 상쾌함 (Refreshment — "positive energy") | Hydration / refresh / sync states |

These are extracted from the character design source PNG; for vector-cleaner
use, the project ships them inside `preview/icons.html`. **Never re-emoji
them** — that defeats the point of the brand.

### Workhorse icon set — Lucide via CDN

```html
<script src="https://unpkg.com/lucide@latest"></script>
<i data-lucide="camera" class="w-5 h-5"></i>
```

Lucide is loaded from `unpkg.com/lucide@latest`. Used at **1.75-px stroke**,
`currentColor`, 20×20 default. Matches the Flutter app's
`Icons.add_a_photo_outlined` family in spirit (outlined, geometric).

> 🚩 **Substitution flag.** The Flutter codebase uses Material Icons via the
> Flutter framework; the closest CDN/web stand-in is Lucide. If the design
> hand-off becomes pixel-critical, swap to a Material Symbols CDN — same
> stroke weight, slightly chunkier feel.

### Animated brand asset — the "thinking" Lottie

The mascot has a 6-second loop where carbon rises inside the body, energy
particles travel to the leaf, and the leaf grows. Use this — *not* a
spinner — for any AI thinking state ≥ 1 s. Keyframes live in
`assets/mascot/tablet-frames/`.

---

## 6. UI Kits & Slides

| Kit | Surface | Files |
|---|---|---|
| **mobile** | Lemon Aid iOS 26 app | [`ui_kits/mobile/`](./ui_kits/mobile/) |

There is no public marketing website in the source tree yet, and no slide
template was provided, so neither is included. Add them here when they
appear.

---

## 7. Caveats — read before using this system

1. **The kit recreates one product (Flutter mobile app).** A marketing
   website skeleton exists in the codebase but is empty; nothing was modeled
   from it.
2. **AtoZ is supplied in 3 weights only.** Intermediate weights (400 / 500 /
   600) fall back to Pretendard. If the full AtoZ family becomes available,
   drop the files into `fonts/` and extend `colors_and_type.css`.
3. **The Lottie source is included for reference** but not wired into HTML
   previews — the static keyframes do the job for design work.
4. **Apple iOS / iPadOS / macOS 26 References** are styling cues. We are
   not lifting Apple proprietary UI components, only the liquid-glass
   surface treatment.

---

## 8. Quick links

- 🎨 Tokens: [`colors_and_type.css`](./colors_and_type.css)
- 🤖 Skill manifest: [`SKILL.md`](./SKILL.md)
- 📱 Mobile UI kit: [`ui_kits/mobile/index.html`](./ui_kits/mobile/index.html)
- 🍋 Mascot reference: [`assets/mascot/character-original.png`](./assets/mascot/character-original.png)
- ⚖️ Compliance copy source: `03_lemon_healthcare/yeong-Lemon-Aid/docs/10-compliance-checklist.md`
