"""exp16 발표용 클린 재평가 — wild(friend 739, 누수 0)에서 top-1 인식률만 측정.

_eval_taxo50.py의 클린 변형(원본 보존). 변경점 4가지:
  1) realworld val 컬럼 제거 — 같은 식당/웹출처가 train에 존재 가능한 약한 지표(Tier1)라 발표 인용 금지.
  2) 지표 라벨 명시: 본 수치는 per-image top-1 인식률(최고conf 박스 클래스==GT AND conf>=0.10).
     mAP50 아님 — mAP50은 studio val(각 런 results.csv: exp16a 0.925 peak e23 / exp16b 0.922 peak e31)이 유일.
  3) per-class는 n>=10 클래스만 출력(꼬리 클래스 per-class 주장 금지 — 전체 CI 위주).
  4) MDE(최소검출효과, alpha=.05 양측, power=.8) 추가 — paired 검정의 검출력 명시.

  5) 지원범위 시나리오(45/40클래스) — wild 검증에서 인식률이 낮은 클래스를 서비스
     미지원으로 정의했을 때의 수치. 제외는 전 모델 동일 분모로 적용하고, 보고 라벨에
     '지원 N클래스 기준'을 명기한다(다른 분모 수치와 혼용 금지). 미지원 클래스는
     표적 실데이터 수집으로 보강 후 재포함하는 것이 목표.

test = friend_contributed 739장(783 − DROP50 44장): 4모델 전부 미학습 = 누수 0 클린 held-out.
DROP50(6) GT 공통 제외 + MERGE(3) 예측·GT 정규화는 원본과 동일(공정 비교).
usage: python -u _eval_exp16_clean.py   (best.pt 없는 모델 skip). device=0 → 학습 중엔 실행 금지.
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

sys.stdout.reconfigure(encoding="utf-8")
DROP50 = {"cold-ramen", "nagasaki-champon", "tteokbokki-jajang", "tteokbokki-cream-rose",
          "hot-pot", "korean-clear-soup"}
MERGE = {"korean-red-soup": "jjigae-red", "noodle-plain": "kalguksu",
         "pork-cutlet-sauced": "pork-cutlet-dry"}
# merge/drop 수혜 기대 클래스 (per-class 표 출력 후보 — n>=10 게이트 적용됨)
RECOVER = ["jjigae-red", "kalguksu", "pork-cutlet-dry", "japanese-ramen", "udon",
           "jjamppong", "seafood-clear-tang", "seafood-spicy-tang"]
WILD = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\wild_keep_dedup_list.txt")
WILD_BASE = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\inbox")
CONF = 0.10
MIN_N = 10  # per-class 주장 최소 표본
# 지원범위 시나리오 — wild 검증에서 인식률이 낮은 클래스를 서비스 미지원으로 정의.
# 제외는 '전 모델 동일 분모'로만 적용하고, 보고 시 라벨에 '지원 N클래스 기준'을 명기한다.
# 미지원 클래스는 표적 실데이터 수집(web_crawl_weak_keep 313장 기확보)으로 보강 후 재포함 목표.
EXCLUDE_45 = {"seafood-jjim", "seafood-spicy-tang", "seafood-clear-tang",
              "squid-dish", "shrimp-dish"}  # wild 인식률 0~0.13
EXCLUDE_40 = EXCLUDE_45 | {"grilled-beef", "jjamppong", "fried-rice",
                           "dumplings", "rice-bowl"}  # + wild 인식률 0.17~0.30
SCENARIOS = [("지원 45클래스", EXCLUDE_45), ("지원 40클래스", EXCLUDE_40)]
MODELS = {
    "exp11": r"C:\Lemon-sin\runs\food_yolo\exp11_yolo26s_taxo59bal1500_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt",
    "exp15a": r"C:\Lemon-sin\runs\food_yolo\exp15a_taxo55_aihub_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt",
    "exp16a": r"C:\Lemon-sin\runs\food_yolo\exp16a_taxo50_aihub_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt",
    "exp16b": r"C:\Lemon-sin\runs\food_yolo\exp16b_taxo50_aihubreal_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt",
}


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


def mde_paired(arr_b, arr_a, z_alpha=1.96, z_power=0.8416):
    """paired 차이의 최소검출효과(alpha=.05 양측, power=.8). per-image d=b-a의 SE 기반."""
    d = np.asarray(arr_b, float) - np.asarray(arr_a, float)
    se = d.std(ddof=1) / np.sqrt(len(d))
    return float((z_alpha + z_power) * se)


def main():
    # wild = friend 폰사진만 (DROP50 제외, GT는 MERGE 정규화) — 4모델 전부 미학습 = 클린
    wild = []
    for ln in WILD.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        fp, c = ln.split("\t")
        if c in DROP50:
            continue
        wild.append((norm(c), WILD_BASE / fp))
    print(f"클린 평가셋: wild(friend) {len(wild)}장 — 4모델 전부 미학습(누수 0)")
    print(f"지표 = per-image top-1 인식률 (strict: 최고conf 박스 클래스==GT AND conf>={CONF}) — mAP50 아님")

    res = {}  # tag -> wild recs
    for tag, w in MODELS.items():
        if not Path(w).exists():
            print(f"[{tag}] best.pt 없음 -> skip")
            continue
        m = YOLO(w)
        res[tag] = eval_model(m, wild)
        print(f"[{tag}] 측정 완료 ({len(res[tag])}장)")
    tags = list(res.keys())

    def strict_arr(recs):
        return [s for _, s, _ in recs]

    def overall(recs, idx):
        return sum(r[idx] for r in recs) / len(recs) if recs else 0.0

    print("\n========== top-1 인식률 (wild, friend 739) — 부트스트랩 95% CI ==========")
    print(f"n={len(wild)}  strict [95%CI] / lenient:")
    for t in tags:
        recs = res[t]; lo, hi = boot_ci(strict_arr(recs))
        print(f"  {t}: {overall(recs,1):.3f} [{lo:.3f}~{hi:.3f}] / {overall(recs,2):.3f}")
    print("참고: mAP50(studio val, results.csv 별개 지표): exp16a 0.925(peak e23) / exp16b 0.922(peak e31)")
    print("      → 발표 표·그래프에서 top-1 인식률(wild)과 mAP50(studio)을 같은 축·같은 이름으로 혼용 금지")

    print("\n[wild] paired 차이검정 (b-a, 95%CI, P(b>a)) + MDE(α=.05, power=.8):")
    pairs = [("exp16b", "exp16a", "실데이터 순효과(핵심)"), ("exp16a", "exp15a", "merge효과(taxo50 vs taxo55)"),
             ("exp16a", "exp11", "drop/merge 누적효과")]
    for b, a, label in pairs:
        if b in res and a in res:
            d, (lo, hi), p = boot_paired(strict_arr(res[b]), strict_arr(res[a]))
            mde = mde_paired(strict_arr(res[b]), strict_arr(res[a]))
            sig = "유의" if (lo > 0 or hi < 0) else "노이즈(0 포함)"
            print(f"  {b}-{a} ({label}): {d:+.3f} [{lo:+.3f}~{hi:+.3f}]  P(b>a)={p:.2f}  MDE=±{mde:.3f}  -> {sig}")

    # 지원범위 시나리오 — 같은 추론 결과에서 GT∈미지원 이미지를 분모에서 제외(전 모델 동일)
    for sc_name, excl in SCENARIOS:
        idx = [i for i, (c, _) in enumerate(wild) if c not in excl]
        sres = {t: [res[t][i] for i in idx] for t in tags}
        print(f"\n========== {sc_name} 기준 (미지원 {len(excl)}: {', '.join(sorted(excl))}) ==========")
        print(f"n={len(idx)} (GT가 미지원 클래스인 {len(wild)-len(idx)}장 제외, 전 모델 동일 분모)  strict [95%CI] / lenient:")
        for t in tags:
            recs = sres[t]; lo, hi = boot_ci(strict_arr(recs))
            print(f"  {t}: {overall(recs,1):.3f} [{lo:.3f}~{hi:.3f}] / {overall(recs,2):.3f}")
        print(f"[{sc_name}] paired 차이검정 (b-a, 95%CI, P(b>a)) + MDE:")
        for b, a, label in pairs:
            if b in sres and a in sres:
                d, (lo, hi), p = boot_paired(strict_arr(sres[b]), strict_arr(sres[a]))
                mde = mde_paired(strict_arr(sres[b]), strict_arr(sres[a]))
                sig = "유의" if (lo > 0 or hi < 0) else "노이즈(0 포함)"
                print(f"  {b}-{a} ({label}): {d:+.3f} [{lo:+.3f}~{hi:+.3f}]  P(b>a)={p:.2f}  MDE=±{mde:.3f}  -> {sig}")
        print(f"  ⚠️ 보고 라벨 = 'top-1 인식률(wild, {sc_name} 기준)'. 다른 분모 수치와 같은 표·축 혼용 금지.")

    # 이미지별 0/1 결과 저장 — 임의 지원범위 조합을 GPU 재실행 없이 오프라인 재계산 가능
    pi_out = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review") / "_eval_exp16_clean_perimage.csv"
    with pi_out.open("w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["image", "gt"] + [f"{t}_strict" for t in tags] + [f"{t}_lenient" for t in tags])
        for i, (gt, fp) in enumerate(wild):
            wr.writerow([str(fp.relative_to(WILD_BASE)), gt]
                        + [res[t][i][1] for t in tags] + [res[t][i][2] for t in tags])
    print(f"\n이미지별 결과: {pi_out.name}")

    aggs = {t: agg_by_class(res[t]) for t in tags}
    print(f"\n[wild] merge/drop 수혜 기대 클래스 strict (n>={MIN_N}만, 미만은 표본부족 표기):")
    print(f"  {'class':20s} {'n':>4s} " + " ".join(f"{t:>7s}" for t in tags))
    for c in RECOVER:
        n = aggs[tags[0]].get(c, [0, 0, 0])[0]
        if n < MIN_N:
            print(f"  {c:20s} {n:>4d} " + f"{'(n<'+str(MIN_N)+' 표본부족 — 주장 금지)':>30s}")
            continue
        row = [f"{aggs[t].get(c,[0,0,0])[1]/n:.2f}" for t in tags]
        print(f"  {c:20s} {n:>4d} " + " ".join(f"{v:>7s}" for v in row))

    # CSV (wild per-class top-1 strict, 정규화 GT 기준, n>=MIN_N 게이트)
    classes = sorted({c for c, _ in wild})
    gated_out = [c for c in classes if aggs[tags[0]].get(c, [0])[0] < MIN_N]
    out = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review") / "_eval_exp16_clean_wild.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["class", "n"] + [f"{t}_top1strict" for t in tags])
        for c in classes:
            n = aggs[tags[0]].get(c, [0])[0]
            if n < MIN_N:
                continue
            wr.writerow([c, n] + [f"{aggs[t].get(c,[0,0,0])[1]/n:.3f}" for t in tags])
    print(f"\nCSV: {out.name} (per-class {len(classes)-len(gated_out)}개, n<{MIN_N} 제외 {len(gated_out)}개: {', '.join(gated_out)})")


if __name__ == "__main__":
    main()
