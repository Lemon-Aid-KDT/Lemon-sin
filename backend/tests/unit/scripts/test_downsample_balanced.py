"""scripts/data/downsample_balanced.py 단위 테스트."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError
from scripts.data._dataset_audit import collect_stems_by_class
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


class TestDatasetAudit:
    """원본 라벨 디렉토리를 스캔해 클래스별 stem 맵을 만든다."""

    def _write_label(self, dir_path: Path, stem: str, lines: list[str]) -> None:
        (dir_path / f"{stem}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_collect_stems_groups_by_first_class_in_file(self, tmp_path: Path) -> None:
        """파일 안 첫 객체의 class_id로 stem이 묶인다."""
        labels = tmp_path / "labels"
        labels.mkdir()
        self._write_label(labels, "img_a", ["3 0.5 0.5 0.2 0.2"])
        self._write_label(labels, "img_b", ["3 0.1 0.1 0.1 0.1", "7 0.9 0.9 0.1 0.1"])
        self._write_label(labels, "img_c", ["7 0.2 0.2 0.1 0.1"])

        result = collect_stems_by_class(labels, num_classes=50)

        assert sorted(result[3]) == ["img_a", "img_b"]
        assert sorted(result[7]) == ["img_b", "img_c"]
        for cid in (0, 1, 2, 4, 5, 6, 8):
            assert result[cid] == []

    def test_collect_stems_ignores_blank_and_invalid_lines(self, tmp_path: Path) -> None:
        """빈 줄과 토큰 부족 줄은 무시한다."""
        labels = tmp_path / "labels"
        labels.mkdir()
        self._write_label(labels, "img_a", ["", "3 0.5 0.5 0.2 0.2", "   ", "bad"])

        result = collect_stems_by_class(labels, num_classes=50)
        assert result[3] == ["img_a"]

    def test_collect_stems_raises_on_out_of_range_class(self, tmp_path: Path) -> None:
        """num_classes 범위 밖 class_id는 명시 예외로 차단한다."""
        labels = tmp_path / "labels"
        labels.mkdir()
        self._write_label(labels, "img_a", ["77 0.5 0.5 0.2 0.2"])

        with pytest.raises(ValueError, match="class_id 77"):
            collect_stems_by_class(labels, num_classes=50)
