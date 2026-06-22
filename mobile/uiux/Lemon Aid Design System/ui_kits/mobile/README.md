# Lemon Aid · Mobile UI kit (iOS 26)

A click-thru, pixel-leaning recreation of the Lemon Aid Flutter app rebuilt in
React + plain CSS. Every component reads from `colors_and_type.css` at the
project root, so the kit and the rest of the design system stay in lockstep.

## What's inside

| File | What it holds |
|---|---|
| `index.html` | Stage: iOS 26 device frame + the React app + a couple of meta blurbs. |
| `App.jsx` | Tiny route state machine — `onboarding → home → capture → review`, plus `chat` and `consent` as their own tabs. Listens to `hashchange` so the screen can be deep-linked. |
| `screens.jsx` | One function per screen: `OnboardingScreen`, `DashboardScreen`, `CaptureScreen`, `ReviewScreen`, `ChatScreen`, `ConsentScreen`. |
| `components.jsx` | Primitives: `AppBar`, `BottomTabs`, `Card`, `Tile`, `Button`, `Pill`, `Disclaimer`, `IngredientRow`, `Mascot`, `Wordmark`, `Bubble`, `SectionHeader`, `Icon`. |
| `ios-frame.jsx` | Liquid-glass iOS 26 device shell (status bar, dynamic island, keyboard). Sourced from the starter library. |
| `mobile-kit.css` | Class layer that React inline-styles can't easily reach — sticky app bar, floating tab capsule, pseudo-state buttons, keyframes. |

## What it covers — and doesn't

The flow mirrors the Flutter `lib/features/{consent,dashboard,supplements}/`
implementation, dressed in the liquid-glass surface language Apple settled on
for iOS 26 / macOS 26.

Covered:

- **Onboarding** — a Pillyze-benchmarked **9-step setup flow** (welcome with mascot
  hero, social sign-in row, BMI line chart + 첫 라벨 분석 무료 쿠폰 → identity
  (name + DOB) → purpose & gender via bottom-sheet pickers → 9-cell health
  concern grid with 추천 badges → ruler-style height / weight / target picker
  → HealthKit / Health Connect prompt → confirmation review → drag-to-customize
  dashboard cube grid with coach-mark → terms agreement) that drops the user
  straight into the camera. Purple → lemon/leaf throughout.
- **Camera** — iOS 26 viewfinder, label-detect guide rectangle, single + multi shutter mode, flash off/on/auto, multi-shot tray with "확인" CTA, gallery thumb, **native-style permission sheet on first launch** (with a denied-state fallback that nudges the user to the gallery).
- **Capture preview** — full-bleed photo after a single shutter, **metadata strip (촬영 일시 · 위치 · 라벨 인식 가능)**, and **다시 촬영 / 이 사진으로 분석** action row.
- **Gallery** — iOS Photos picker grid (3 × N), single + multi selection with iOS numbered badges, frosted "N장 분석 시작" CTA, LIVE photo badge, **album switcher dropdown** (모든 사진 · 즐겨찾기 · 최근 항목 · 영양제 라벨 · 식단 사진), **heart badge for favourites**, and **selection metadata banner**.
- **Dashboard** — today's one-line brief (the glass card), four metric tiles
  for the five outputs, recent supplements list, bottom disclaimer.
- **Capture** — picker → analyzing (mascot + 5-step timeline) → ready
  (ingredient candidates with checkbox UX).
- **Review** — product fields, low-confidence checkbox confirmation, schedule
  chips, save CTA.
- **Chat** — agent / user bubbles, "AI is a helping hand" disclosure, mascot
  typing-indicator, frosted composer.
- **Consent (Settings)** — required + optional consents, hard-block
  disclaimer for prescriptions / labs.

### New reusable primitives (from the Pillyze pass)

- `<ProgressBar value max />` — top-of-step gradient progress.
- `<BottomSheet open title desc onClose>` — slide-up modal.
- `<RulerPicker value unit min max step onChange />` — horizontal ruler input.
- `<ConcernCard icon label badge gradient selected onClick />` — 3D-icon grid card.
- `<Cube label value unit sub progress full />` — customizable dashboard cube.
- `<CoachMark title body bottom />` — backdrop + tooltip.
- `<Dots count active />` — page indicator.
- `<Carousel value onChange interval>` — auto-advancing, swipe-enabled slider.
- `<NumericKeypad onKey>` — iOS-style 3×4 in-app keypad (1–9 with letters, 0, ⌫).
- `<WheelPicker columns>` / `<WheelColumn items value onChange />` — iOS-style scroll-snap wheel for time/date.
- `<ReorderList items onReorder renderItem handleSelector>` — pointer-based drag-reorder list with insert indicator.
- `<CoachMarkSequence steps onDone container>` — multi-step walkthrough with spotlight + tooltip + skip/next.

Not covered (would be the next batch):

- HealthKit / Health Connect connection screens
- Per-output detail pages (drilling into 부족 영양소 or 주의 성분)
- Real keyboard input flows (we show the iOS keyboard occasionally but inputs
  are still demo-state)

## How to use it

Open `index.html` directly — every dependency loads from a CDN
(`react@18.3.1`, `@babel/standalone@7.29.0`, `lucide@0.452.0`). No build step.

Navigate with the bottom tabs, or jump straight to any screen with a hash:
`#home`, `#capture`, `#review`, `#chat`, `#consent`, `#onboarding`. The
capture flow's internal sub-stages (`camera`, `gallery`, `analyzing`,
`ready`) can also be set from a parent page by posting
`{type: 'lm-set-stage', stage: 'gallery', mode: 'multi'}` — the design-system
preview cards for the photo intake screens use this.

## When you extract components for production

The components are intentionally cosmetic — no proper accessibility wiring, no
form validation, no real network calls. Lift the visual treatment, then back
it with whichever framework owns your codebase (Flutter, SwiftUI, React Native).
The token names in `colors_and_type.css` are stable; copy them out as-is.
