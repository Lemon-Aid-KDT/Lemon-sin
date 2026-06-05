"""실험 비교 맵 — 발표용 다듬은 버전 (모던 색감·라운드 막대·수치 강조)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib import patheffects as pe
from matplotlib.patches import FancyBboxPatch

SOFT = [pe.withSimplePatchShadow(offset=(2.5, -2.5), shadow_rgbFace="#9aa7bd", alpha=0.22)]
SOFT_S = [pe.withSimplePatchShadow(offset=(1.6, -1.6), shadow_rgbFace="#9aa7bd", alpha=0.28)]

FP = r"C:\Windows\Fonts\malgun.ttf"
font_manager.fontManager.addfont(FP)
FAM = font_manager.FontProperties(fname=FP).get_name()
plt.rcParams["font.family"] = FAM
plt.rcParams["axes.unicode_minus"] = False

EXP = [
    (1, 0.846, "exp01", "yolov8n", "50cls", "p0"),
    (2, 0.697, "exp02", "yolo11s", "50cls", "inc"),
    (3, 0.790, "exp03", "yolov8n", "balanced", "p0"),
    (4, 0.806, "exp04", "yolov8n", "증강", "p0"),
    (5, 0.804, "exp05", "yolov8n", "복제", "p0"),
    (6, 0.824, "exp06", "yolo11s", "taxo63", "p1"),
    (7, 0.849, "exp07", "yolo26s", "taxo63", "p1"),
    (8, 0.830, "exp08", "yolo11s", "taxo63", "p1"),
    (9, 0.837, "exp09", "yolo26s", "taxo62", "p1"),
    (10, 0.882, "exp10", "yolo26s", "taxo59", "p1"),
    (11, 0.895, "exp11", "yolo26s", "cap1500", "best"),
]
MAP = {e[0]: e[1] for e in EXP}
# 파스텔(말랑) 팔레트
C_P0, C_P1, C_INC, C_BEST = "#aeb9d4", "#86efc4", "#dfe4ee", "#34d399"
FILL = {"p0": C_P0, "p1": C_P1, "inc": C_INC, "best": C_BEST}
INK = "#3f4756"
BASE = 0.75

fig, ax = plt.subplots(figsize=(13.5, 13.5))  # 정사각형 비율
fig.patch.set_facecolor("white")

# phase 밴드 (아주 옅게)
ax.axvspan(0.45, 5.5, color="#f1f5f9", zorder=0)
ax.axvspan(5.5, 11.7, color="#ecfdf5", zorder=0)

# phase 라벨 (필 형태)
for x, txt, fc, tc in [(3.0, "Phase 0 · 표준 튜닝 (50클래스)", "#e2e8f0", "#475569"),
                       (8.6, "Phase 1 · 택소노미 재설계 + 정리 (taxo63→59)", "#d1fae5", "#047857")]:
    ax.text(x, 1.052, txt, ha="center", va="center", fontsize=14.5, fontweight="bold", color=tc,
            bbox=dict(boxstyle="round,pad=0.5", fc=fc, ec="none"))

# 라운드 막대
for x, m, nm, mdl, ds, st in EXP:
    top = max(m, BASE + 0.004)
    fc = FILL[st]
    bar = FancyBboxPatch((x - 0.30, BASE), 0.60, top - BASE,
                 boxstyle="round,pad=0,rounding_size=0.022", fc=fc, ec="none",
                 mutation_aspect=0.022, zorder=3)
    bar.set_path_effects(SOFT)
    ax.add_patch(bar)
    vtxt = f"{m:.3f}" + ("?" if st == "best" and False else "*" if st == "inc" else "")
    ax.text(x, top + 0.007, vtxt, ha="center", fontsize=12.5, fontweight="bold",
            color=C_BEST if st == "best" else INK, zorder=6)
    ax.text(x, BASE - 0.008, nm, ha="center", va="top", fontsize=11.5, fontweight="bold", color=INK, zorder=6)
    ax.text(x, BASE - 0.022, f"{mdl}\n{ds}", ha="center", va="top", fontsize=8.4, color="#64748b", zorder=6)

# best 강조 별
ax.text(11, MAP[11] + 0.028, "★ 최고", ha="center", fontsize=10.5, fontweight="bold", color=C_BEST, zorder=7)

# 추세선 (부드럽게)
for seg in ([e for e in EXP if e[0] <= 5 and e[5] != "inc"], [e for e in EXP if e[0] >= 6]):
    xs = [e[0] for e in seg]; ys = [e[1] for e in seg]
    ax.plot(xs, ys, ls=(0, (1, 2.5)), lw=1.6, color="#c3ccdb", zorder=2,
            marker="o", ms=6.5, mfc="white", mec="#c3ccdb", mew=1.6)

ax.plot([5.5, 5.5], [BASE - 0.04, 1.02], ls=":", color="#cbd5e1", lw=1.4, zorder=1)


def bracket(xs, lane, color, label, sub):
    ly = 0.905 + lane * 0.052
    x1, x2 = min(xs), max(xs)
    ax.plot([x1, x2], [ly, ly], color=color, lw=2.6, solid_capstyle="round", zorder=5)
    for xt in xs:
        ax.plot([xt, xt], [MAP[xt] + 0.005, ly], color=color, lw=1.3, alpha=0.65,
                solid_capstyle="round", zorder=4)
    t = ax.text((x1 + x2) / 2, ly + 0.006, label, ha="center", va="bottom", fontsize=10.5,
                fontweight="bold", color="white",
                bbox=dict(boxstyle="round,pad=0.46", fc=color, ec="none"), zorder=6)
    t.set_path_effects(SOFT_S)
    ax.text((x1 + x2) / 2, ly - 0.006, sub, ha="center", va="top", fontsize=8.6, color=color, zorder=6)


bracket([3, 4, 5], 0, "#f59e0b", "증강·복제", "효과 없음 (공정비교)")
bracket([7, 8], 0, "#8b5cf6", "모델 11s→26s", "+0.019")
bracket([9, 10], 0, "#0d9488", "약점 클래스 정리", "+0.045")
bracket([10, 11], 1, "#ea580c", "데이터 증량", "과적합 ↓ · val +0.018")
bracket([7, 9], 2, "#e11d48", "라벨노이즈 정리", "fried-chicken +0.226")

# Phase0→1 전환
ax.annotate("", xy=(6, BASE - 0.05), xytext=(5, BASE - 0.05),
            arrowprops=dict(arrowstyle="-|>", color="#3b82f6", lw=2.2), zorder=4)
ax.text(5.5, BASE - 0.058, "택소노미 재설계 (50→taxo63, 혼동군 분할)  ·  탕 0.56→0.84 · 면 0.55→0.92",
        ha="center", va="top", fontsize=9.3, color="#1d4ed8", fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.32", fc="#eff6ff", ec="#bfdbfe", lw=1))

# 제목 + Hero (axes 기준 — 비율 바뀌어도 안정)
ax.text(0.0, 1.10, "음식 탐지 모델 — 실험 비교 맵", transform=ax.transAxes, ha="left", va="bottom",
        fontsize=22, fontweight="bold", color=INK)
ax.text(0.0, 1.072, "막대 높이 = 정확도 상승  ·  연결선 = 무엇과 무엇을 비교했나",
        transform=ax.transAxes, ha="left", va="bottom", fontsize=11.5, color="#64748b")
ax.text(1.0, 1.108, "전체 mAP50", transform=ax.transAxes, ha="right", va="bottom", fontsize=11, color="#64748b")
ax.text(1.0, 1.066, "0.824 → 0.895", transform=ax.transAxes, ha="right", va="bottom",
        fontsize=20, fontweight="bold", color=C_BEST)

ax.set_xlim(0.2, 11.95)
ax.set_ylim(BASE - 0.078, 1.10)
ax.set_yticks([0.75, 0.80, 0.85, 0.90])
ax.set_yticklabels(["0.75", "0.80", "0.85", "0.90"], fontsize=10, color="#94a3b8")
ax.set_xticks([])
for s in ["top", "right", "bottom", "left"]:
    ax.spines[s].set_visible(False)
ax.tick_params(length=0)
ax.grid(axis="y", ls=(0, (2, 4)), color="#e2e8f0", zorder=0)
ax.text(11.9, BASE - 0.075, "* exp02 미완 · 0.75 기준 절단축(차이 강조) · 2026-06-03",
        ha="right", fontsize=8, color="#94a3b8")

OUT = Path(r"C:\Lemon-sin\docs\deliverables\2026-06-03-experiment-comparison-map-presentation.png")
plt.subplots_adjust(top=0.88, left=0.06, right=0.96, bottom=0.06)
plt.savefig(OUT, dpi=160, facecolor="white")
print("WROTE", OUT)
