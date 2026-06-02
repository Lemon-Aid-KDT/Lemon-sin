"""실험 비교 맵 — 막대(높이=mAP, 상승 추세) + 계단식 비교 브래킷(겹침 제거).

박스를 mAP 막대로 그려 '정확도가 오르는' 느낌을 살리고, 통제비교는 막대 위
빈 공간에 계단식 브래킷으로 둔다. 브래킷 연결선은 각 막대의 실제 높이(값)로 내려온다.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

FP = r"C:\Windows\Fonts\malgun.ttf"
font_manager.fontManager.addfont(FP)
plt.rcParams["font.family"] = font_manager.FontProperties(fname=FP).get_name()
plt.rcParams["axes.unicode_minus"] = False

# (x, mAP, 이름, 모델, 데이터셋, 상태)
EXP = [
    (1, 0.846, "exp01", "yolov8n", "50cls full", "done"),
    (2, 0.697, "exp02", "yolo11s", "50cls", "incomplete"),
    (3, 0.790, "exp03", "yolov8n", "50cls bal", "done"),
    (4, 0.806, "exp04", "yolov8n", "50cls 증강", "done"),
    (5, 0.804, "exp05", "yolov8n", "50cls 복제", "done"),
    (6, 0.824, "exp06", "yolo11s", "taxo63", "done"),
    (7, 0.849, "exp07", "yolo26s", "taxo63", "done"),
    (8, 0.830, "exp08", "yolo11s", "taxo63 b16", "done"),
    (9, 0.837, "exp09", "yolo26s", "taxo62", "done"),
    (10, 0.882, "exp10", "yolo26s", "taxo59", "done"),
    (11, 0.895, "exp11", "yolo26s", "taxo59 cap1500", "done"),
]
MAP = {e[0]: e[1] for e in EXP}
COL = {"done_p0": "#1565c0", "done_p1": "#1b5e20", "incomplete": "#9e9e9e", "pending": "#ef6c00"}

BASE = 0.75  # 막대 기준선(절단축 — 0.79~0.88 차이 강조). 값 라벨 병기로 정직성 유지.
fig, ax = plt.subplots(figsize=(18.5, 10.5))

# phase 배경
ax.axvspan(0.45, 5.55, color="#e3f2fd", alpha=0.5, zorder=0)
ax.axvspan(5.55, 11.75, color="#e8f5e9", alpha=0.5, zorder=0)

# === 막대 (높이 = mAP) + 상승 추세선 ===
tops = []
for x, m, nm, mdl, ds, st in EXP:
    key = "incomplete" if st == "incomplete" else "pending" if st == "pending" else ("done_p0" if x <= 5 else "done_p1")
    c = COL[key]
    top = max(m, BASE + 0.004)
    ax.bar(x, top - BASE, bottom=BASE, width=0.62, color=c, alpha=0.30, edgecolor=c, lw=2.2, zorder=3)
    # 값 (막대 안 상단)
    vtxt = f"{m:.3f}" + ("?" if st == "pending" else "*" if st == "incomplete" else "")
    ax.text(x, top - 0.006, vtxt, ha="center", va="top", fontsize=12.5, fontweight="bold", color="#1a1a1a", zorder=6)
    # 라벨 (기준선 아래)
    ax.text(x, BASE - 0.006, nm, ha="center", va="top", fontsize=12, fontweight="bold", color=c, zorder=6)
    ax.text(x, BASE - 0.020, mdl, ha="center", va="top", fontsize=9, color="#444", zorder=6)
    ax.text(x, BASE - 0.031, ds, ha="center", va="top", fontsize=8.2, color="#666", zorder=6)
    if st != "incomplete":
        tops.append((x, m))
# 상승 추세선 (막대 꼭대기 연결, Phase별 분리)
for seg in ([t for t in tops if t[0] <= 5], [t for t in tops if t[0] >= 6]):
    xs, ys = zip(*seg)
    ax.plot(xs, ys, ls="--", lw=1.6, color="#999", alpha=0.8, zorder=2, marker="o", ms=4, mfc="#666", mec="#666")

ax.plot([5.55, 5.55], [BASE - 0.035, 1.058], ls="--", color="#999", lw=1.4, zorder=1)
ax.text(3.0, 1.045, "Phase 0 — 표준 튜닝 (원본 50클래스)", ha="center", fontsize=14.5, fontweight="bold", color="#1565c0")
ax.text(8.6, 1.045, "Phase 1 — 택소노미 재설계 + 정리 (taxo63→59)", ha="center", fontsize=14.5, fontweight="bold", color="#1b5e20")

# === 계단식 비교 브래킷 (막대 위, 연결선은 각 막대 높이로) ===
def bracket(xs, lane, color, label, sub=""):
    ly = 0.905 + lane * 0.050
    x1, x2 = min(xs), max(xs)
    ax.plot([x1, x2], [ly, ly], color=color, lw=2.4, zorder=5)
    for xt in xs:
        ax.plot([xt, xt], [MAP[xt] + 0.004, ly], color=color, lw=1.3, alpha=0.85, zorder=4)
    ax.text((x1 + x2) / 2, ly + 0.004, label, ha="center", va="bottom", fontsize=10.5,
            fontweight="bold", color=color, zorder=6)
    if sub:
        ax.text((x1 + x2) / 2, ly - 0.004, sub, ha="center", va="top", fontsize=8.2, color=color, zorder=6)

bracket([3, 4, 5], 0, "#e65100", "⑤ 증강·복제 (exp03·04·05)",
        "동일 val: base 0.826 > 증강 0.806 ≈ 복제 0.805 → 효과 없음")
bracket([7, 8], 0, "#6a1b9a", "① 모델 11s→26s", "+0.019")
bracket([9, 10], 0, "#00695c", "③ 약점3 _DROP", "+0.045")
bracket([10, 11], 1, "#ef6c00", "④ 데이터량 cap 500→1500", "val +0.018 · 과적합갭 0.117→0.097")
bracket([7, 9], 2, "#d84315", "② chicken-galbi 라벨정리", "fried-chicken 0.67→0.90 (+0.226)")

# Phase0→1 전환 (기준선 아래)
ax.annotate("", xy=(6, BASE - 0.052), xytext=(5, BASE - 0.052),
            arrowprops=dict(arrowstyle="-|>", color="#1565c0", lw=2.2), zorder=4)
ax.text(5.5, BASE - 0.060, "Phase 0 → 1 : 택소노미 재설계 (50 → taxo63, 혼동군 분할)  ·  탕 0.56→0.84 · 면 0.55→0.92\n⚠ 클래스셋 달라 raw mAP 직접비교 불가 — 레버별 효과로 해석",
        ha="center", va="top", fontsize=9.3, color="#1565c0", fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.3", fc="#e3f2fd", ec="#1565c0", lw=1.2))

ax.set_xlim(0.2, 12.0)
ax.set_ylim(BASE - 0.085, 1.075)
ax.set_ylabel("best mAP50  (※ 0.75 기준 절단축 — 차이 강조)", fontsize=11)
ax.set_yticks([0.75, 0.80, 0.85, 0.90])
ax.set_xticks([])
for s in ["top", "right", "bottom"]:
    ax.spines[s].set_visible(False)
ax.set_title("음식 탐지 실험 비교 맵 (exp01–11) — 막대=정확도 상승 / 브래킷=무엇과 무엇을 비교",
             fontsize=18, fontweight="bold", pad=14)
ax.text(11.95, BASE - 0.082, "* exp02 미완(ep3)   exp11 조기종료 e33(best e18)   |   2026-06-02", ha="right", fontsize=8.5, color="#888")

OUT = Path(r"C:\Lemon-sin\docs\deliverables\2026-06-02-experiment-comparison-map.png")
plt.savefig(OUT, dpi=150, bbox_inches="tight")
print("WROTE", OUT)
