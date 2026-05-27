"""scripts/data/downsample_balanced.py 단위 테스트."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from scripts.data._manifest_models import ClassManifest, TrainManifest


class TestManifestModels:
    """매니페스트 Pydantic v2 모델 검증."""

    def test_class_manifest_serializes_sorted_stems(self) -> None:
        """ClassManifest는 stems를 정렬된 리스트로 직렬화한다."""
        cm = ClassManifest(class_id=3, class_name="fried-rice", stems=["b", "a", "c"])
        dumped = cm.model_dump()
        assert dumped["stems"] == ["a", "b", "c"]

    def test_train_manifest_round_trip_via_json(self) -> None:
        """TrainManifest는 JSON 직렬화 → 역직렬화 후 동일하다."""
        manifest = TrainManifest(
            seed=42,
            cap_per_class=500,
            classes=[
                ClassManifest(class_id=0, class_name="salad", stems=["s1", "s2"]),
                ClassManifest(class_id=1, class_name="mixed-rice-bowl", stems=["m1"]),
            ],
        )

        loaded = TrainManifest.model_validate_json(manifest.model_dump_json())

        assert loaded == manifest

    def test_train_manifest_rejects_duplicate_class_ids(self) -> None:
        """TrainManifest는 중복 class_id를 거부한다."""
        with pytest.raises(ValueError, match="duplicate"):
            TrainManifest(
                seed=42,
                cap_per_class=500,
                classes=[
                    ClassManifest(class_id=0, class_name="salad", stems=["s1"]),
                    ClassManifest(class_id=0, class_name="salad", stems=["s2"]),
                ],
            )

    def test_class_manifest_rejects_out_of_range_class_id(self) -> None:
        """class_id는 0~49 범위 밖이면 거부된다."""
        with pytest.raises(ValidationError):
            ClassManifest(class_id=50, class_name="ghost", stems=["g1"])
