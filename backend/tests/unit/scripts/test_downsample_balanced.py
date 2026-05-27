"""scripts/data/downsample_balanced.py 단위 테스트."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError
from scripts.data._dataset_audit import collect_stems_by_class
from scripts.data._manifest_models import ClassManifest, TrainManifest
from scripts.data.downsample_balanced import (
    copy_full_split,
    copy_selected_pairs,
    run_downsample,
    select_stems_per_class,
    write_dataset_yaml,
)


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


class TestCopyAndYaml:
    """파일 복사와 data.yaml 작성."""

    def _make_pair(self, root: Path, stem: str) -> None:
        (root / "images").mkdir(parents=True, exist_ok=True)
        (root / "labels").mkdir(parents=True, exist_ok=True)
        (root / "images" / f"{stem}.jpg").write_bytes(b"\xff\xd8\xff\xe0 fake jpg")
        (root / "labels" / f"{stem}.txt").write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")

    def test_copy_selected_pairs_copies_only_listed_stems(self, tmp_path: Path) -> None:
        """선택된 stem만 새 train으로 복사한다."""
        src = tmp_path / "src" / "train"
        for s in ("a", "b", "c", "d"):
            self._make_pair(src, s)
        dst = tmp_path / "dst" / "train"

        copied = copy_selected_pairs(src, dst, selected_stems=["a", "c"])

        assert copied == 2
        assert sorted(p.stem for p in (dst / "images").glob("*.jpg")) == ["a", "c"]
        assert sorted(p.stem for p in (dst / "labels").glob("*.txt")) == ["a", "c"]

    def test_copy_selected_pairs_raises_on_missing_image(self, tmp_path: Path) -> None:
        """라벨은 있는데 이미지가 없으면 즉시 실패한다."""
        src = tmp_path / "src" / "train"
        (src / "labels").mkdir(parents=True)
        (src / "labels" / "ghost.txt").write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
        (src / "images").mkdir()
        dst = tmp_path / "dst" / "train"

        with pytest.raises(FileNotFoundError, match=r"ghost\.jpg"):
            copy_selected_pairs(src, dst, selected_stems=["ghost"])

    def test_copy_full_split_copies_all_pairs(self, tmp_path: Path) -> None:
        """val 전체 복사."""
        src = tmp_path / "src" / "val"
        for s in ("v1", "v2", "v3"):
            self._make_pair(src, s)
        dst = tmp_path / "dst" / "val"

        copied = copy_full_split(src, dst)

        assert copied == 3
        assert sorted(p.stem for p in (dst / "images").glob("*.jpg")) == ["v1", "v2", "v3"]

    def test_write_dataset_yaml_contains_path_and_names(self, tmp_path: Path) -> None:
        """data.yaml에 path, train, val, nc, names가 정확히 기록된다."""
        dst = tmp_path / "balanced_500"
        dst.mkdir()
        names = ["salad", "mixed-rice-bowl", "rice-bowl"]

        yaml_path = write_dataset_yaml(dst, names=names)

        content = yaml_path.read_text(encoding="utf-8")
        assert f"path: {dst.as_posix()}" in content
        assert "train: train/images" in content
        assert "val: val/images" in content
        assert "nc: 3" in content
        assert "- salad" in content
        assert "- mixed-rice-bowl" in content


class TestRunDownsample:
    """run_downsample 전체 파이프라인 (소형 데이터셋으로)."""

    def _make_dataset(self, root: Path, train_counts: dict[int, int], val_count: int) -> None:
        """class_id → 개수 dict 로 가짜 train을 만들고 val은 단일 클래스로 채운다."""
        (root / "train" / "images").mkdir(parents=True)
        (root / "train" / "labels").mkdir(parents=True)
        (root / "val" / "images").mkdir(parents=True)
        (root / "val" / "labels").mkdir(parents=True)

        for cid, n in train_counts.items():
            for i in range(n):
                stem = f"t_c{cid}_{i:04d}"
                (root / "train" / "images" / f"{stem}.jpg").write_bytes(b"\xff\xd8")
                (root / "train" / "labels" / f"{stem}.txt").write_text(
                    f"{cid} 0.5 0.5 0.2 0.2\n", encoding="utf-8"
                )
        for i in range(val_count):
            stem = f"v_{i:04d}"
            (root / "val" / "images" / f"{stem}.jpg").write_bytes(b"\xff\xd8")
            (root / "val" / "labels" / f"{stem}.txt").write_text(
                "0 0.5 0.5 0.2 0.2\n", encoding="utf-8"
            )

    def test_run_downsample_caps_train_keeps_val(self, tmp_path: Path) -> None:
        """train은 cap 적용, val은 무변경."""
        src = tmp_path / "src"
        self._make_dataset(src, train_counts={0: 800, 1: 50}, val_count=30)
        dst = tmp_path / "dst_balanced"
        names = ["cls_zero", "cls_one"]

        result = run_downsample(
            src_root=src,
            dst_root=dst,
            class_names=names,
            cap_per_class=500,
            seed=42,
        )

        assert result.train_copied == 550
        assert result.val_copied == 30

        assert len(list((dst / "train" / "images").glob("*.jpg"))) == 550
        assert len(list((dst / "val" / "images").glob("*.jpg"))) == 30
        assert (dst / "data.yaml").exists()
        assert (dst / "_manifest" / "train_manifest.json").exists()
        assert (dst / "_manifest" / "class_counts_original.csv").exists()
        assert (dst / "_manifest" / "class_counts_balanced.csv").exists()

    def test_run_downsample_is_deterministic(self, tmp_path: Path) -> None:
        """두 번 돌렸을 때 매니페스트가 비트 동일."""
        src = tmp_path / "src"
        self._make_dataset(src, train_counts={0: 800, 1: 700}, val_count=10)
        names = ["cls_zero", "cls_one"]

        dst_a = tmp_path / "dst_a"
        dst_b = tmp_path / "dst_b"
        run_downsample(src, dst_a, names, cap_per_class=500, seed=42)
        run_downsample(src, dst_b, names, cap_per_class=500, seed=42)

        manifest_a = (dst_a / "_manifest" / "train_manifest.json").read_text(encoding="utf-8")
        manifest_b = (dst_b / "_manifest" / "train_manifest.json").read_text(encoding="utf-8")
        assert manifest_a == manifest_b

    def test_run_downsample_applies_val_cap_when_given(self, tmp_path: Path) -> None:
        """val_cap_per_class 가 주어지면 val도 클래스별 cap 적용된다."""
        src = tmp_path / "src"
        # train cap 적용용 + val에 클래스 0이 80, 클래스 1이 5 들어가도록
        self._make_dataset(src, train_counts={0: 200, 1: 5}, val_count=0)
        # val을 직접 만들기 (val_count=0이면 안 만들었으니 추가)
        (src / "val" / "images").mkdir(parents=True, exist_ok=True)
        (src / "val" / "labels").mkdir(parents=True, exist_ok=True)
        for cid, n in {0: 80, 1: 5}.items():
            for i in range(n):
                stem = f"v_c{cid}_{i:04d}"
                (src / "val" / "images" / f"{stem}.jpg").write_bytes(b"\xff\xd8")
                (src / "val" / "labels" / f"{stem}.txt").write_text(
                    f"{cid} 0.5 0.5 0.2 0.2\n", encoding="utf-8"
                )

        dst = tmp_path / "dst"
        names = ["cls_zero", "cls_one"]

        result = run_downsample(
            src_root=src,
            dst_root=dst,
            class_names=names,
            cap_per_class=500,
            seed=42,
            val_cap_per_class=50,
        )

        # train: 200 + 5 = 205 (cap 500 안 걸림)
        assert result.train_copied == 205
        # val: 클래스 0이 80 → 50으로 cap, 클래스 1은 5 그대로 → 55
        assert result.val_copied == 55
        assert (dst / "_manifest" / "val_manifest.json").exists()
        assert (dst / "_manifest" / "val_class_counts_original.csv").exists()
        assert (dst / "_manifest" / "val_class_counts_balanced.csv").exists()

    def test_run_downsample_val_cap_none_copies_full_val(self, tmp_path: Path) -> None:
        """val_cap_per_class=None(기본값)이면 val 전체 복사 (기존 동작 호환)."""
        src = tmp_path / "src"
        self._make_dataset(src, train_counts={0: 100}, val_count=42)
        dst = tmp_path / "dst"

        result = run_downsample(
            src_root=src,
            dst_root=dst,
            class_names=["cls_zero"],
            cap_per_class=500,
            seed=42,
        )

        assert result.val_copied == 42
        assert not (dst / "_manifest" / "val_manifest.json").exists()
