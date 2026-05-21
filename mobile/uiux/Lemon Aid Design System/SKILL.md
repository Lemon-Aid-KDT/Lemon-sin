---
name: lemon-aid-design
description: Use this skill to generate well-branded interfaces and assets for Lemon Aid (레몬에이드) — an AI-powered chronic-disease companion mobile app built around an Apple-style liquid-glass aesthetic and a 3D glass-lemon mascot. Covers production code, throwaway prototypes, slides, marketing artwork. Contains essential design guidelines, colors, type, fonts, mascot assets, and UI kit components for prototyping.
user-invocable: true
---

Read the README.md file within this skill, and explore the other available
files. The directory layout:

```
.
├── README.md                  ← product context + content/visual/iconography foundations
├── colors_and_type.css        ← single source of truth for tokens (CSS vars)
├── fonts/                     ← AtoZ Thin / ExtraBold / Black (display)
├── assets/mascot/             ← character cutout, gold variant, loader keyframes, Lottie JSON
├── preview/                   ← Design System tab cards (small focused HTML files)
└── ui_kits/mobile/            ← iOS 26 click-thru prototype (React + plain CSS)
```

If creating visual artifacts (slides, mocks, throwaway prototypes, etc.), copy
needed assets out of `assets/mascot/` and link `colors_and_type.css`. Reach for
single-character mascot frames (`assets/mascot/tablet-frames/*.png`) for hero
images — `character-cutout.png` is the *reference sheet*, not a stand-alone
glyph.

If working on production code, lift the token names from `colors_and_type.css`
verbatim — they're stable. The mobile UI kit at `ui_kits/mobile/` shows how the
tokens combine into screens; recreate the relevant primitives in your target
framework (Flutter, SwiftUI, React Native, …).

If the user invokes this skill without other guidance, ask them what they want
to build or design, ask a few questions (audience, surface, copy direction,
how Korean-first the result should be, whether they want one option or
several), and act as an expert designer who outputs HTML artifacts *or*
production code, depending on the need.

## Non-negotiables

These appear in the brand brief and Korean compliance docs both. Hold the line:

1. **No system emoji** anywhere in product UI. Use bespoke liquid-glass SVG
   glyphs from `preview/icons.html`, or Lucide via CDN.
2. **No diagnosis / prescription / cure language.** The agent is a "helping
   hand" — see the *Compliance copy* table in README.md.
3. **Every recommendation screen ends with the medical disclaimer block.**
   Three variants live in `preview/component-disclaimer.html`.
4. **AI is a co-pilot.** Always preview before saving. Approval gates are
   first-class UX, not afterthoughts.
5. **Korean first, formal but warm.** Use `~합니다 / ~합시다 / ~해보세요`.
   English appears only for ingredient symbols and developer-mode strings.
6. **Warm canvas, never cool grey.** `--canvas` (`#FBF8EC`) or `--paper`
   (`#FFFDF6`) for backgrounds.
7. **One lemon CTA per screen.** Multiple yellow halos defeat the signal.

## Source repositories

This skill was distilled from:

- `Lemon-Aid-KDT/Lemon-sin` (branch `yeong-tech`) — primary working tree
- `HorangEe02/Project_yeong` (branch `main`, `03_lemon_healthcare/` subtree)

Both are public; explore `docs/Nutrition-docs/` there for richer compliance,
algorithm and OCR-pipeline context.
