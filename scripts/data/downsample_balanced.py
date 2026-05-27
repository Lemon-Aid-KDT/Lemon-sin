"""AI Hub YOLO 50 클래스 train 다운샘플링.

원본 train의 클래스당 이미지 수를 상한(기본 500)으로 자르고,
이미지+라벨을 새 폴더로 복사한다. val은 원본 전체를 복사한다.

샘플링은 spec §3.1대로 seed 고정 랜덤(random.sample on sorted stems).

Reference:
    docs/superpowers/specs/2026-05-27-aihub-yolo-balanced500-yolo11s-design.md
"""

from __future__ import annotations

import random
import shutil
from pathlib import Path


def select_stems_per_class(
    stems_by_class: dict[int, list[str]],
    cap_per_class: int,
    seed: int,
) -> dict[int, list[str]]:
    """클래스별로 시드 고정 랜덤 샘플링을 적용한다.

    클래스의 원본 개수가 cap_per_class 초과면 cap만큼 sample,
    이하면 전체를 그대로 유지한다. 결과는 정렬된 stem 리스트로 반환한다.

    재현성: 같은 seed + 같은 입력(stems_by_class의 각 리스트가 동일 set)이면
    출력이 비트 단위로 동일하다. 입력 순서는 sorted()로 정규화하므로 무관.

    Args:
        stems_by_class: class_id → 원본 stem 리스트.
        cap_per_class: 클래스당 상한.
        seed: random.seed에 사용할 정수.

    Returns:
        class_id → 선택된 stem 리스트 (정렬됨). 입력의 모든 키 보존.

    Examples:
        >>> result = select_stems_per_class({0: ["a", "b", "c", "d"]}, cap_per_class=2, seed=42)
        >>> len(result[0])
        2
    """
    rng = random.Random(seed)
    output: dict[int, list[str]] = {}
    for cid in sorted(stems_by_class.keys()):
        canonical = sorted(stems_by_class[cid])
        if len(canonical) <= cap_per_class:
            output[cid] = list(canonical)
        else:
            picked = rng.sample(canonical, cap_per_class)
            output[cid] = sorted(picked)
    return output


def copy_selected_pairs(src_split: Path, dst_split: Path, selected_stems: list[str]) -> int:
    """src의 images/labels에서 stem 짝을 dst로 복사한다.

    Args:
        src_split: 원본 split 루트 (예: aihub_yolo_50/train).
        dst_split: 대상 split 루트 (예: aihub_yolo_50_balanced_500/train).
        selected_stems: 복사할 파일 stem 리스트 (확장자 제외).

    Returns:
        복사된 짝 개수.

    Raises:
        FileNotFoundError: stem의 jpg가 src에 없는 경우.
    """
    (dst_split / "images").mkdir(parents=True, exist_ok=True)
    (dst_split / "labels").mkdir(parents=True, exist_ok=True)

    count = 0
    for stem in selected_stems:
        src_img = src_split / "images" / f"{stem}.jpg"
        src_lbl = src_split / "labels" / f"{stem}.txt"
        if not src_img.exists():
            raise FileNotFoundError(f"missing image: {src_img.name}")
        shutil.copy2(src_img, dst_split / "images" / src_img.name)
        shutil.copy2(src_lbl, dst_split / "labels" / src_lbl.name)
        count += 1
    return count


def copy_full_split(src_split: Path, dst_split: Path) -> int:
    """split 전체(images + labels)를 dst로 복사한다.

    val을 다운샘플 없이 전체 그대로 옮길 때 사용한다.

    Args:
        src_split: 원본 split 루트.
        dst_split: 대상 split 루트.

    Returns:
        복사된 이미지 개수.
    """
    stems = sorted(p.stem for p in (src_split / "images").glob("*.jpg"))
    return copy_selected_pairs(src_split, dst_split, selected_stems=stems)


def write_dataset_yaml(dst_root: Path, names: list[str]) -> Path:
    """다운샘플 결과 폴더에 data.yaml을 작성한다.

    Args:
        dst_root: aihub_yolo_50_balanced_500 폴더 절대 경로.
        names: 클래스 이름 리스트 (순서 = class_id).

    Returns:
        생성된 data.yaml 경로.
    """
    yaml_path = dst_root / "data.yaml"
    lines = [
        "# YOLO dataset config - balanced_500 subset (train downsampled to <=500/class)",
        f"path: {dst_root.as_posix()}",
        "train: train/images",
        "val: val/images",
        "",
        f"nc: {len(names)}",
        "names:",
        *[f"  - {n}" for n in names],
        "",
    ]
    yaml_path.write_text("\n".join(lines), encoding="utf-8")
    return yaml_path
