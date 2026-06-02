"""exp03(balanced) vs exp04(증강) vs exp05(중복) per-class AP 비교 — CPU.

소수클래스 증강/복제가 개별 클래스 정확도를 어떻게 바꿨는지 검증.
세 모델 모두 동일 val(exp04 val100)에 돌려 공정 비교. GPU 학습 중이라 device=cpu.
"""

from __future__ import annotations

import csv
import glob
from collections import Counter
from pathlib import Path

import yaml
from ultralytics import YOLO

BASE = Path(r"C:\Lemon-sin\data\food_images\processed")
RUNS = Path(r"C:\Lemon-sin\runs\food_yolo")
COMMON_VAL = BASE / "aihub_yolo_50_minority_aug_train500_val100" / "data.yaml"  # 공통 val
MODELS = {
    "exp03_base": RUNS / "exp03_yolov8n_balanced500_pc1_b48_w8_cache_disk_det_true" / "weights" / "best.pt",
    "exp04_aug": RUNS / "exp04_yolov8n_minorityaug_train500_val100_pc1_b48_w8_cache_disk_det_true" / "weights" / "best.pt",
    "exp05_dup": RUNS / "exp05_yolov8n_minoritydup_train500_val100_pc1_b48_w8_cache_disk_det_true" / "weights" / "best.pt",
}
OUT = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review\minority_aug_per_class.csv")


def first_cls(lbl: Path) -> int | None:
    for ln in lbl.read_text().splitlines():
        p = ln.split()
        if len(p) >= 5:
            return int(p[0])
    return None


def main() -> None:
    names = yaml.safe_load((BASE / "aihub_yolo_50_balanced_500" / "data.yaml").read_text(encoding="utf-8"))["names"]
    names = list(names.values()) if isinstance(names, dict) else list(names)
    # 소수클래스 식별 = exp03 baseline train < 500
    cnt: Counter[int] = Counter()
    for lbl in glob.glob(str(BASE / "aihub_yolo_50_balanced_500" / "train" / "labels" / "*.txt")):
        c = first_cls(Path(lbl))
        if c is not None:
            cnt[c] += 1
    minority = {names[c] for c, n in cnt.items() if n < 500}

    ap: dict[str, dict[str, float]] = {}
    for tag, w in MODELS.items():
        print(f"[CPU val] {tag} ...", flush=True)
        m = YOLO(str(w))
        r = m.val(data=str(COMMON_VAL), split="val", imgsz=640, device="cpu",
                  workers=2, verbose=False, plots=False)
        ap[tag] = {m.names[ci]: float(r.box.ap50[i]) for i, ci in enumerate(r.box.ap_class_index)}
        print(f"  overall mAP50={float(r.box.map50):.4f}", flush=True)

    rows = []
    for nm in names:
        a3, a4, a5 = ap["exp03_base"].get(nm), ap["exp04_aug"].get(nm), ap["exp05_dup"].get(nm)
        rows.append({
            "class": nm, "minority": nm in minority,
            "exp03_base": round(a3, 4) if a3 is not None else "",
            "exp04_aug": round(a4, 4) if a4 is not None else "",
            "exp05_dup": round(a5, 4) if a5 is not None else "",
            "aug_delta": round(a4 - a3, 4) if (a3 is not None and a4 is not None) else "",
            "dup_delta": round(a5 - a3, 4) if (a3 is not None and a5 is not None) else "",
        })
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["class", "minority", "exp03_base", "exp04_aug", "exp05_dup", "aug_delta", "dup_delta"])
        w.writeheader()
        w.writerows(rows)

    def mean(xs):
        xs = [x for x in xs if isinstance(x, (int, float))]
        return sum(xs) / len(xs) if xs else 0.0

    mino = [r for r in rows if r["minority"]]
    majo = [r for r in rows if not r["minority"]]
    print("\n=== 소수클래스 평균 AP (증강/복제 대상) ===")
    print(f"  baseline {mean([r['exp03_base'] for r in mino]):.4f} -> aug {mean([r['exp04_aug'] for r in mino]):.4f} (Δ{mean([r['aug_delta'] for r in mino]):+.4f}) / dup {mean([r['exp05_dup'] for r in mino]):.4f} (Δ{mean([r['dup_delta'] for r in mino]):+.4f})")
    print("=== 다수클래스 평균 AP (보강 안 함) ===")
    print(f"  baseline {mean([r['exp03_base'] for r in majo]):.4f} -> aug {mean([r['exp04_aug'] for r in majo]):.4f} (Δ{mean([r['aug_delta'] for r in majo]):+.4f}) / dup {mean([r['exp05_dup'] for r in majo]):.4f} (Δ{mean([r['dup_delta'] for r in majo]):+.4f})")
    print(f"\n소수클래스 {len(mino)}개 개별:")
    for r in sorted(mino, key=lambda x: x["aug_delta"] if isinstance(x["aug_delta"], (int, float)) else 0):
        print(f"  {r['class']:22s} base {r['exp03_base']} -> aug {r['exp04_aug']}(Δ{r['aug_delta']:+}) dup {r['exp05_dup']}(Δ{r['dup_delta']:+})")
    print(f"\nWROTE {OUT}")


if __name__ == "__main__":
    main()
