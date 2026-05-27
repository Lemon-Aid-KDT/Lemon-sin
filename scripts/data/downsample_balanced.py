"""AI Hub YOLO 50 클래스 train 다운샘플링.

원본 train의 클래스당 이미지 수를 상한(기본 500)으로 자르고,
이미지+라벨을 새 폴더로 복사한다. val은 원본 전체를 복사한다.

샘플링은 spec §3.1대로 seed 고정 랜덤(random.sample on sorted stems).

Reference:
    docs/superpowers/specs/2026-05-27-aihub-yolo-balanced500-yolo11s-design.md
"""

from __future__ import annotations

import random


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
