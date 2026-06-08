"""taxo50 평가 — exp11/15a/16a/16b를 wild + realworld val에 name기반 측정.

핵심: taxo50는 merge가 있어 GT/예측을 MERGE 맵으로 '정규화' 후 비교(공정).
  - DROP50(6) GT 이미지는 전 모델 공통 제외(같은 분모).
  - MERGE(3) 적용: 예측·GT 모두 타깃명으로 정규화 → exp11(korean-red-soup)과 exp16(jjigae-red) 공정 비교.
비교: exp16a vs exp15a/exp11 = drop/merge효과 / exp16b vs exp16a = realworld 순효과(핵심).
usage: python _eval_taxo50.py   (best.pt 없는 모델 skip). device=0 → 학습 중엔 실행 금지.
"""
from __future__ import annotations
import glob, os, sys, csv
from collections import defaultdict
from pathlib import Path
import cv2, numpy as np, yaml
from ultralytics import YOLO

sys.stdout.reconfigure(encoding="utf-8")
DROP50 = {"cold-ramen", "nagasaki-champon", "tteokbokki-jajang", "tteokbokki-cream-rose",
          "hot-pot", "korean-clear-soup"}
MERGE = {"korean-red-soup": "jjigae-red", "noodle-plain": "kalguksu",
         "pork-cutlet-sauced": "pork-cutlet-dry"}
# merge/drop 수혜 기대 클래스
RECOVER = ["jjigae-red", "kalguksu", "pork-cutlet-dry", "japanese-ramen", "udon",
           "jjamppong", "seafood-clear-tang", "seafood-spicy-tang"]
AIHUB59 = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo59_bal1500")
WILD = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\wild_keep_dedup_list.txt")
WILD_BASE = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\inbox")
REAL = Path(r"C:\Lemon-sin\data\food_images\processed\realworld_collected_v1")
CONF = 0.10
MODELS = {
    "exp11": r"C:\Lemon-sin\runs\food_yolo\exp11_yolo26s_taxo59bal1500_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt",
    "exp15a": r"C:\Lemon-sin\runs\food_yolo\exp15a_taxo55_aihub_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt",
    "exp16a": r"C:\Lemon-sin\runs\food_yolo\exp16a_taxo50_aihub_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt",
    "exp16b": r"C:\Lemon-sin\runs\food_yolo\exp16b_taxo50_aihubreal_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt",
}
names59 = yaml.safe_load((AIHUB59 / "data.yaml").read_text(encoding="utf-8"))["names"]
names59 = names59 if isinstance(names59, list) else [names59[i] for i in sorted(names59)]


def norm(name):
    return MERGE.get(name, name) if name else name


def top1(m, im):
    r = m.predict(im, conf=0.01, verbose=False, device=0)[0]
    if not len(r.boxes):
        return None, 0.0
    bi = int(np.argmax(r.boxes.conf.tolist()))
    return m.names[int(r.boxes.cls[bi])], float(r.boxes.conf[bi])


def eval_model(m, items):
    """items 순서대로 (gt_n, strict0/1, lenient0/1) 기록 — 부트스트랩용 per-image."""
    recs = []
    for gt_n, p in items:
        im = cv2.imread(str(p))
        if im is None:
            recs.append((gt_n, 0, 0)); continue
        name, cf = top1(m, im)
        match = norm(name) == gt_n
        recs.append((gt_n, int(match and cf >= CONF), int(match)))
    return recs


def agg_by_class(recs):
    agg = defaultdict(lambda: [0, 0, 0])
    for gt_n, s, l in recs:
        a = agg[gt_n]; a[0] += 1; a[1] += s; a[2] += l
    return agg


def boot_ci(arr, B=2000, seed=42):
    """arr=0/1 per-image. 부트스트랩 95% CI of mean."""
    rng = np.random.default_rng(seed)
    a = np.asarray(arr, float); n = len(a)
    if n == 0:
        return (0.0, 0.0)
    means = a[rng.integers(0, n, size=(B, n))].mean(axis=1)
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


def boot_paired(arr_b, arr_a, B=2000, seed=42):
    """같은 테스트셋 paired diff(b-a) 95% CI + P(b>a). 같은 인덱스 재표본."""
    rng = np.random.default_rng(seed)
    b = np.asarray(arr_b, float); a = np.asarray(arr_a, float); n = len(b)
    idx = rng.integers(0, n, size=(B, n))
    d = b[idx].mean(axis=1) - a[idx].mean(axis=1)
    return float(d.mean()), (float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))), float((d > 0).mean())


def main():
    # wild (DROP50 제외, GT 정규화)
    wild = []
    for ln in WILD.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        fp, c = ln.split("\t")
        if c in DROP50:
            continue
        wild.append((norm(c), WILD_BASE / fp))
    # realworld val
    rval = []
    for lf in glob.glob(str(REAL / "val" / "labels" / "*.txt")):
        ln = open(lf).readline().split()
        if not ln:
            continue
        nm = names59[int(ln[0])]
        if nm in DROP50:
            continue
        img = REAL / "val" / "images" / (os.path.basename(lf)[:-4] + ".jpg")
        if img.exists():
            rval.append((norm(nm), img))
    print(f"평가셋(taxo50, merge정규화): wild {len(wild)} | realworld val {len(rval)}")

    res = {}  # tag -> {"wild": recs, "rval": recs}
    for tag, w in MODELS.items():
        if not Path(w).exists():
            print(f"[{tag}] best.pt 없음 -> skip")
            continue
        m = YOLO(w)
        res[tag] = {"wild": eval_model(m, wild), "rval": eval_model(m, rval)}
        print(f"[{tag}] 측정 완료")
    tags = list(res.keys())

    def strict_arr(recs):
        return [s for _, s, _ in recs]

    def overall(recs, idx):
        return sum(r[idx] for r in recs) / len(recs) if recs else 0.0

    print("\n================= taxo50 평가 요약 (부트스트랩 95% CI) =================")
    for setname, key in [("WILD", "wild"), ("realworld val", "rval")]:
        n = len(res[tags[0]][key])
        print(f"\n[{setname}] n={n}  strict [95%CI] / lenient:")
        for t in tags:
            recs = res[t][key]; lo, hi = boot_ci(strict_arr(recs))
            print(f"  {t}: {overall(recs,1):.3f} [{lo:.3f}~{hi:.3f}] / {overall(recs,2):.3f}")

    # paired 차이검정 (같은 테스트셋, WILD)
    print("\n[WILD] paired 차이검정 (b-a, 95%CI, P(b>a)):")
    pairs = [("exp16b", "exp16a", "실데이터 순효과"), ("exp16a", "exp15a", "merge효과(taxo50 vs taxo55)"),
             ("exp16a", "exp11", "drop/merge 누적효과")]
    for b, a, label in pairs:
        if b in res and a in res:
            d, (lo, hi), p = boot_paired(strict_arr(res[b]["wild"]), strict_arr(res[a]["wild"]))
            sig = "유의" if (lo > 0 or hi < 0) else "노이즈(0 포함)"
            print(f"  {b}-{a} ({label}): {d:+.3f} [{lo:+.3f}~{hi:+.3f}]  P(b>a)={p:.2f}  -> {sig}")

    print("\n[WILD] merge/drop 수혜 기대 클래스 strict:")
    aggs = {t: agg_by_class(res[t]["wild"]) for t in tags}
    print(f"  {'class':20s} " + " ".join(f"{t:>7s}" for t in tags))
    for c in RECOVER:
        row = []
        for t in tags:
            a = aggs[t].get(c, [0, 0, 0])
            row.append(f"{a[1]/a[0]:.2f}" if a[0] else "  -")
        print(f"  {c:20s} " + " ".join(f"{v:>7s}" for v in row))
    # CSV (wild per-class, 정규화 GT 기준)
    classes = sorted({c for c, _ in wild})
    out = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review") / "_eval_taxo50_wild.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f); wr.writerow(["class", "n"] + [f"{t}_strict" for t in tags])
        for c in classes:
            n = aggs[tags[0]].get(c, [0])[0]
            wr.writerow([c, n] + [f"{aggs[t].get(c,[0,0,0])[1]/max(1,n):.3f}" for t in tags])
    print(f"\nCSV: {out.name}")


if __name__ == "__main__":
    main()
