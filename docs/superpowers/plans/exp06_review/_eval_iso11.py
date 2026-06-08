"""11클래스 격리 실험(exp17) 평가 — A/B/C + exp11/exp13 을 모든 실데이터(11클래스)에 측정.

테스트셋 = friend(wild) + team + web crawl (전부). 이 5개 모델은 team/web/friend를
학습에 안 썼으므로(iso11=AIHub+selectstar / exp11=AIHub / exp13=AIHub+ss) 누수 없음.
name기반 strict + 부트스트랩 95%CI + paired + 출처별 분해. device=0 → 학습중 실행금지.
"""
from __future__ import annotations
import glob, os, sys
from collections import defaultdict
from pathlib import Path
import cv2, numpy as np, yaml
from ultralytics import YOLO

sys.stdout.reconfigure(encoding="utf-8")
NAMES11 = {"takoyaki", "black-bean-noodles", "udon", "bulgogi", "dim-sum",
           "japanese-ramen", "savory-pancake", "jjigae-red", "raw-fish",
           "rice-noodle-soup", "mixed-rice-bowl"}
WILD = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\wild_keep_dedup_list.txt")
WBASE = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\inbox")
REAL = Path(r"C:\Lemon-sin\data\food_images\processed\realworld_collected_v1")
AIHUB59 = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo59_bal1500")
CONF = 0.10
R = r"C:\Lemon-sin\runs\food_yolo"
def find(pat):
    g = glob.glob(f"{R}\\{pat}\\weights\\best.pt")
    return g[0] if g else f"{R}\\{pat}\\weights\\best.pt"
MODELS = {
    "A_aihub": find("exp17a_iso11_aihub_*"),
    "B_mix": find("exp17b_iso11_both_*"),
    "C_ss": find("exp17c_iso11_ss_*"),
    "exp11(full59 AIHub)": r"C:\Lemon-sin\runs\food_yolo\exp11_yolo26s_taxo59bal1500_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt",
    "exp13(full59 +ss)": find("exp13_*"),
}
names59 = yaml.safe_load((AIHUB59 / "data.yaml").read_text(encoding="utf-8"))["names"]
names59 = names59 if isinstance(names59, list) else [names59[i] for i in sorted(names59)]


def top1(m, im):
    r = m.predict(im, conf=0.01, verbose=False, device=0)[0]
    if not len(r.boxes):
        return None, 0.0
    bi = int(np.argmax(r.boxes.conf.tolist()))
    return m.names[int(r.boxes.cls[bi])], float(r.boxes.conf[bi])


def eval_model(m, items):
    recs = []
    for gt, p, src in items:
        im = cv2.imread(str(p))
        if im is None:
            recs.append((gt, 0, src)); continue
        name, cf = top1(m, im)
        recs.append((gt, int(name == gt and cf >= CONF), src))
    return recs


def boot_ci(a, B=2000, seed=42):
    rng = np.random.default_rng(seed); a = np.asarray(a, float); n = len(a)
    if n == 0:
        return (0, 0)
    m = a[rng.integers(0, n, (B, n))].mean(1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def boot_paired(b, a, B=2000, seed=42):
    rng = np.random.default_rng(seed); b = np.asarray(b, float); a = np.asarray(a, float); n = len(b)
    idx = rng.integers(0, n, (B, n)); d = b[idx].mean(1) - a[idx].mean(1)
    return float(d.mean()), (float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))), float((d > 0).mean())


def build_test():
    items = []  # (gt, path, source)
    # friend (wild)
    for ln in WILD.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            fp, c = ln.split("\t")
            if c in NAMES11:
                items.append((c, WBASE / fp, "friend"))
    # realworld team/web (train+val 둘 다, iso11/exp11/exp13 학습에 미사용)
    for split in ("train", "val"):
        for lf in glob.glob(str(REAL / split / "labels" / "*.txt")):
            line = open(lf).readline().split()
            if not line:
                continue
            gt = names59[int(line[0])]
            if gt not in NAMES11:
                continue
            stem = os.path.basename(lf)[:-4]
            src = "team" if stem.startswith("rw_team") else ("web" if stem.startswith("rw_web") else "rw")
            img = REAL / split / "images" / f"{stem}.jpg"
            if img.exists():
                items.append((gt, img, src))
    return items


def main():
    items = build_test()
    bysrc = defaultdict(int)
    for _, _, s in items:
        bysrc[s] += 1
    print(f"테스트셋(11클래스, 전 실데이터): {len(items)}장 = " + " + ".join(f"{k} {v}" for k, v in sorted(bysrc.items())))
    res = {}
    for tag, w in MODELS.items():
        if not Path(w).exists():
            print(f"[{tag}] best.pt 없음 -> skip"); continue
        res[tag] = eval_model(YOLO(w), items)
        print(f"[{tag}] 측정 완료")
    tags = list(res.keys())
    sa = lambda recs, src=None: [s for _, s, sr in recs if src is None or sr == src]
    ov = lambda recs, src=None: (lambda a: sum(a) / len(a) if a else 0)(sa(recs, src))

    print("\n========== exp17 (전 실데이터) wild 결과 (부트스트랩 95%CI) ==========")
    srcs = ["(전체)"] + sorted(bysrc)
    print(f"  {'model':22s} " + " ".join(f"{s:>14s}" for s in srcs))
    for t in tags:
        cells = []
        for s in srcs:
            sub = None if s == "(전체)" else s
            arr = sa(res[t], sub)
            if arr:
                lo, hi = boot_ci(arr)
                cells.append(f"{sum(arr)/len(arr):.2f}[{lo:.2f}-{hi:.2f}]")
            else:
                cells.append("-")
        print(f"  {t:22s} " + " ".join(f"{c:>14s}" for c in cells))

    print("\npaired 차이검정 — 전체 (b-a, 95%CI, P):")
    for b, a, lab in [("C_ss", "A_aihub", "selectstar vs AIHub 단독"),
                      ("B_mix", "A_aihub", "절반을 ss로 교체(수량동일)"),
                      ("B_mix", "C_ss", "절반을 AIHub로 교체"),
                      ("B_mix", "exp13(full59 +ss)", "격리효과(11 vs 59)")]:
        if b in res and a in res:
            d, (lo, hi), p = boot_paired(sa(res[b]), sa(res[a]))
            sig = "유의" if (lo > 0 or hi < 0) else "노이즈(0포함)"
            print(f"  {b} - {a} ({lab}): {d:+.3f} [{lo:+.3f}~{hi:+.3f}] P={p:.2f} -> {sig}")

    print("\n클래스별 strict (전체):")
    aggs = {t: defaultdict(lambda: [0, 0]) for t in tags}
    for t in tags:
        for gt, s, _ in res[t]:
            aggs[t][gt][0] += 1; aggs[t][gt][1] += s
    print(f"  {'class':20s} {'n':>3s} " + " ".join(f"{t.split('(')[0][:8]:>8s}" for t in tags))
    for c in sorted(NAMES11):
        n = next((aggs[t][c][0] for t in tags if c in aggs[t]), 0)
        row = " ".join(f"{(aggs[t][c][1]/aggs[t][c][0] if aggs[t][c][0] else 0):8.2f}" for t in tags)
        print(f"  {c:20s} {n:3d} {row}")


if __name__ == "__main__":
    main()
