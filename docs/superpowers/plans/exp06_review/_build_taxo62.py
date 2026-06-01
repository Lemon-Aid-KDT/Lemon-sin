"""taxonomy v3(62클래스) 데이터셋 빌드.

exp09용: chicken-galbi 라벨노이즈 정리(B12003->fried-chicken, B12144->_DROP)로 클래스 삭제.
근거: exp07_chicken_label_audit.md.

424코드 라벨을 63 최종클래스로 리매핑하고, 이미지는 하드링크로 재사용한다.
_DROP 코드 라인은 제거하고, 라벨이 비면 이미지도 제외한다.

usage:
    python _build_taxo62.py --dry      # 클래스/물량만 검증, 파일 미생성
    python _build_taxo62.py            # 실제 빌드
"""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

SRC = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_split")
DST = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo62")
MAP_CSV = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review\exp09_taxonomy_v3_mapping.csv")

# 한글 신규 클래스 -> romanized (기존 영문 클래스는 그대로 유지)
ROMAN = {
    "한식맑은국": "korean-clear-soup", "한식빨간국": "korean-red-soup", "양식수프": "western-cream-soup",
    "일본라멘": "japanese-ramen", "한국라면(빨간)": "korean-ramyeon-red", "냉라멘": "cold-ramen",
    "떡볶이(빨간)": "tteokbokki-red", "떡볶이(크림로제)": "tteokbokki-cream-rose", "떡볶이(자장)": "tteokbokki-jajang",
    "돈가스(마른)": "pork-cutlet-dry", "돈가스(소스국물)": "pork-cutlet-sauced",
    "해물매운탕": "seafood-spicy-tang", "해물맑은탕": "seafood-clear-tang", "해물찜": "seafood-jjim",
    "칼국수": "kalguksu", "쌀국수": "rice-noodle-soup", "국수일반": "noodle-plain",
    "찌개류(붉은)": "jjigae-red", "된장찌개": "doenjang-jjigae",
    "짬뽕": "jjamppong", "나가사끼짬뽕": "nagasaki-champon",
}


def roman(name: str) -> str:
    return ROMAN.get(name, name)


def remap_label_lines(lines: list[str], idx2new: dict[int, int | None]) -> list[str]:
    """라벨 라인들의 class_id를 새 id로 바꾸고, drop 대상(None) 라인은 제거한다."""
    out: list[str] = []
    for raw in lines:
        s = raw.strip()
        if not s:
            continue
        parts = s.split()
        if len(parts) < 5:
            continue
        new = idx2new.get(int(parts[0]), "__MISSING__")
        if new is None:
            continue  # _DROP
        if new == "__MISSING__":
            raise ValueError(f"label class id {parts[0]} not in mapping")
        parts[0] = str(new)
        out.append(" ".join(parts))
    return out


def _selftest() -> None:
    assert remap_label_lines(["5 0.5 0.5 0.2 0.2", "9 0.1 0.1 0.1 0.1"], {5: 2, 9: None}) == \
        ["2 0.5 0.5 0.2 0.2"]
    assert remap_label_lines(["", "  ", "5 0.5 0.5 0.2 0.2"], {5: 0}) == ["0 0.5 0.5 0.2 0.2"]


def main(dry: bool) -> None:
    _selftest()
    a2c = json.load(open(SRC / "yolo_class_index_split.json", encoding="utf-8"))["aihub_to_class"]
    final_of_code = {r["aihub_code"]: r["final_class"]
                     for r in csv.DictReader(open(MAP_CSV, encoding="utf-8-sig"))}

    # idx(424) -> final romanized class (or None for drop)
    idx2finalname: dict[int, str | None] = {}
    for code, v in a2c.items():
        fc = final_of_code.get(code, v["orig_roboflow_class"])
        idx2finalname[v["new_index"]] = None if fc == "_DROP" else roman(fc)

    classes = sorted({n for n in idx2finalname.values() if n})
    name2id = {n: i for i, n in enumerate(classes)}
    idx2new: dict[int, int | None] = {
        idx: (name2id[n] if n else None) for idx, n in idx2finalname.items()
    }

    print(f"최종 클래스 수: {len(classes)}")
    agg = defaultdict(lambda: [0, 0, 0])  # split-agnostic image/instance count filled below

    stats = {"train": [0, 0, 0], "val": [0, 0, 0]}  # imgs_kept, imgs_dropped, instances
    for split in ("train", "val"):
        src_lbl = SRC / split / "labels"
        src_img = SRC / split / "images"
        dst_lbl = DST / split / "labels"
        dst_img = DST / split / "images"
        if not dry:
            dst_lbl.mkdir(parents=True, exist_ok=True)
            dst_img.mkdir(parents=True, exist_ok=True)
        for lbl in src_lbl.glob("*.txt"):
            out = remap_label_lines(lbl.read_text(encoding="utf-8").splitlines(), idx2new)
            if not out:
                stats[split][1] += 1
                continue
            stats[split][0] += 1
            stats[split][2] += len(out)
            for ln in out:
                agg[classes[int(ln.split()[0])]][0 if split == "train" else 1] += 1
            if not dry:
                (dst_lbl / lbl.name).write_text("\n".join(out) + "\n", encoding="utf-8")
                img = src_img / (lbl.stem + ".jpg")
                dlink = dst_img / img.name
                if img.exists() and not dlink.exists():
                    os.link(img, dlink)  # 하드링크(동일 볼륨, 디스크 중복 없음)

    if not dry:
        names_block = "\n".join(f"  {i}: {n}" for i, n in enumerate(classes))
        (DST / "data.yaml").write_text(
            f"path: {DST.as_posix()}\ntrain: train/images\nval: val/images\n"
            f"nc: {len(classes)}\nnames:\n{names_block}\n", encoding="utf-8")

    for split in ("train", "val"):
        kept, dropped, inst = stats[split]
        print(f"{split}: kept={kept} dropped(empty)={dropped} instances={inst}")
    if dry:
        print("\n[DRY] 클래스별 train/val 인스턴스 (상위/하위 점검):")
        for n in classes:
            print(f"  {name2id[n]:2d} {n:24s} train_inst={agg[n][0]:5d} val_inst={agg[n][1]:4d}"
                  + ("  ⚠️val0" if agg[n][1] == 0 else ""))
    else:
        print(f"\nWROTE {DST}\\data.yaml  (nc={len(classes)})")


if __name__ == "__main__":
    main(dry="--dry" in sys.argv)
