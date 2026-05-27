"""scripts/data/downsample_balanced.py 단위 테스트."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError
from scripts.data._dataset_audit import collect_stems_by_class
from scripts.data._manifest_models import ClassManifest, TrainManifest
from scripts.data.downsample_balanced import select_stems_per_class


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


class TestSelectStemsPerClass:
    """spec §3.1: seed=42 고정 랜덤 샘플링."""

    def test_caps_at_500_when_class_has_more(self) -> None:
        """500장 초과 클래스는 정확히 500장으로 잘린다."""
        stems_by_class = {0: [f"img_{i:04d}" for i in range(1200)]}
        selected = select_stems_per_class(stems_by_class, cap_per_class=500, seed=42)
        assert len(selected[0]) == 500

    def test_keeps_all_when_class_below_cap(self) -> None:
        """500장 미만 클래스는 그대로 보존된다."""
        stems_by_class = {0: [f"img_{i:04d}" for i in range(123)]}
        selected = select_stems_per_class(stems_by_class, cap_per_class=500, seed=42)
        assert sorted(selected[0]) == sorted(stems_by_class[0])

    def test_deterministic_across_runs(self) -> None:
        """같은 seed+입력 → 같은 출력 (비트 동일)."""
        stems_by_class = {cid: [f"c{cid}_{i:05d}" for i in range(1500)] for cid in range(50)}
        first = select_stems_per_class(stems_by_class, cap_per_class=500, seed=42)
        second = select_stems_per_class(stems_by_class, cap_per_class=500, seed=42)
        for cid in range(50):
            assert first[cid] == second[cid]

    def test_different_seed_produces_different_selection(self) -> None:
        """seed가 다르면 선택이 달라진다 (랜덤성 sanity check)."""
        stems_by_class = {0: [f"img_{i:04d}" for i in range(1500)]}
        a = select_stems_per_class(stems_by_class, cap_per_class=500, seed=42)
        b = select_stems_per_class(stems_by_class, cap_per_class=500, seed=43)
        assert set(a[0]) != set(b[0])

    def test_input_order_does_not_affect_output(self) -> None:
        """입력 리스트 순서를 섞어도 같은 시드면 같은 결과 (sorted() 정규화)."""
        base = [f"img_{i:04d}" for i in range(1500)]
        sorted_input = {0: sorted(base)}
        shuffled_input = {0: list(reversed(base))}
        a = select_stems_per_class(sorted_input, cap_per_class=500, seed=42)
        b = select_stems_per_class(shuffled_input, cap_per_class=500, seed=42)
        assert sorted(a[0]) == sorted(b[0])
