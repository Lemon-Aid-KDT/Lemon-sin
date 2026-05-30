"""taxo63 -> balanced (train<=500 / val<=100, seed=42 고정 랜덤) 다운샘플.

클래스별로 라벨의 class_id 기준 그룹화 후 상한 적용. 이미지는 하드링크.
exp03 balanced 방법론과 동일(시드 고정·sorted·random.sample). 단일객체 데이터 전제.
"""

from __future__ import annotations

import os
import random
import shutil
from collections import defaultdict
from pathlib import Path

SRC = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo63")
DST = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo63_bal500")
SEED = 42
CAPS = {"train": 500, "val": 100}


def class_names_from_yaml(p: Path) -> list[str]:
    names: list[str] = []
    in_names = False
    for raw in p.read_text(encoding="utf-8").splitlines():
        if raw.startswith("names:"):
            in_names = True
            continue
        if in_names:
            s = raw.strip()
            if ":" in s and s.split(":")[0].strip().isdigit():
                names.append(s.split(":", 1)[1].strip())
            elif s and not raw.startswith(" "):
                break
    return names


def first_class(lbl: Path) -> int | None:
    for ln in lbl.read_text(encoding="utf-8").splitlines():
        parts = ln.split()
        if len(parts) >= 5:
            return int(parts[0])
    return None


def main() -> None:
    names = class_names_from_yaml(SRC / "data.yaml")
    rng = random.Random(SEED)
    summary = {}
    for split, cap in CAPS.items():
        groups: dict[int, list[str]] = defaultdict(list)
        for lbl in sorted((SRC / split / "labels").glob("*.txt")):
            c = first_class(lbl)
            if c is not None:
                groups[c].append(lbl.stem)
        selected: list[str] = []
        for c in sorted(groups):
            stems = sorted(groups[c])
            if len(stems) > cap:
                stems = sorted(rng.sample(stems, cap))
            selected.extend(stems)
        dimg = DST / split / "images"
        dlbl = DST / split / "labels"
        dimg.mkdir(parents=True, exist_ok=True)
        dlbl.mkdir(parents=True, exist_ok=True)
        for stem in selected:
            src_img = SRC / split / "images" / f"{stem}.jpg"
            dst_img = dimg / f"{stem}.jpg"
            if src_img.exists() and not dst_img.exists():
                os.link(src_img, dst_img)
            shutil.copy2(SRC / split / "labels" / f"{stem}.txt", dlbl / f"{stem}.txt")
        summary[split] = len(selected)
        print(f"{split}: selected={len(selected)} (classes={len(groups)}, cap={cap})")

    block = "\n".join(f"  {i}: {n}" for i, n in enumerate(names))
    (DST / "data.yaml").write_text(
        f"path: {DST.as_posix()}\ntrain: train/images\nval: val/images\n"
        f"nc: {len(names)}\nnames:\n{block}\n", encoding="utf-8")
    print(f"WROTE {DST}\\data.yaml  nc={len(names)}  train={summary['train']} val={summary['val']}")


if __name__ == "__main__":
    main()
