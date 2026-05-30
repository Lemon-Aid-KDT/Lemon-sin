"""Unit tests for the minority augmentation and capped validation dataset script."""

from __future__ import annotations

import tempfile
import unittest
from random import Random
from pathlib import Path

from PIL import Image

from data.food_images.scripts.create_minority_aug_valcap_dataset import (
    AugmentationConfig,
    GenerationMode,
    YoloBox,
    augment_image_and_boxes,
    build_augmentation_config,
    collect_stems_by_class,
    create_dataset,
    read_yolo_label,
    select_capped_stems_by_class,
)


class MinorityAugValCapDatasetTest(unittest.TestCase):
    """Small end-to-end checks for minority train augmentation and val capping."""

    def test_select_capped_stems_is_deterministic(self) -> None:
        """The same class stems and seed always produce the same capped selection."""
        stems_by_class = {0: ["b", "a", "c"], 1: ["x", "z", "y"]}

        first = select_capped_stems_by_class(stems_by_class, cap_per_class=2, seed=42)
        second = select_capped_stems_by_class(stems_by_class, cap_per_class=2, seed=42)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 4)

    def test_augment_image_and_boxes_keeps_target_box_valid(self) -> None:
        """A generated sample keeps the requested class with normalized bbox values."""
        image = Image.new("RGB", (64, 64), (180, 120, 80))
        boxes = [YoloBox(class_id=1, x_center=0.5, y_center=0.5, width=0.5, height=0.5)]

        augmented_image, augmented_boxes = augment_image_and_boxes(
            image=image,
            boxes=boxes,
            target_class_id=1,
            rng=Random(42),
            config=AugmentationConfig(),
        )

        self.assertEqual(augmented_image.size, (64, 64))
        self.assertEqual(len(augmented_boxes), 1)
        box = augmented_boxes[0]
        self.assertEqual(box.class_id, 1)
        self.assertGreater(box.width, 0.0)
        self.assertGreater(box.height, 0.0)
        self.assertLessEqual(box.x_center, 1.0)
        self.assertLessEqual(box.y_center, 1.0)

    def test_create_dataset_augments_train_and_caps_val(self) -> None:
        """Train minority classes are increased while val is capped without augmentation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            src = root / "src"
            dst = root / "dst"
            self._write_data_yaml(src, ["class-zero", "class-one", "class-two"])
            self._make_split(src, "train", {0: 2, 1: 1, 2: 4})
            self._make_split(src, "val", {0: 3, 1: 2, 2: 5})

            summary = create_dataset(
                src_root=src,
                dst_root=dst,
                train_target_per_class=3,
                val_cap_per_class=2,
                seed=42,
                config=AugmentationConfig(
                    max_rotation_degrees=5.0,
                    crop_min_ratio=0.9,
                    crop_max_ratio=1.0,
                ),
            )

            self.assertEqual(summary.copied_train_original, 7)
            self.assertEqual(summary.generated_train_augmented, 3)
            self.assertEqual(summary.copied_val_selected, 6)
            self.assertEqual(summary.train_final_counts, {0: 3, 1: 3, 2: 4})
            self.assertEqual(summary.val_selected_counts, {0: 2, 1: 2, 2: 2})
            self.assertTrue((dst / "data.yaml").exists())
            self.assertTrue((dst / "_manifest" / "minority_aug_valcap_manifest.json").exists())
            self.assertEqual(len(list((dst / "train" / "images").glob("*.jpg"))), 10)
            self.assertEqual(len(list((dst / "train" / "labels").glob("*.txt"))), 10)

            generated_label = next((dst / "train" / "labels").glob("*_aug_c01_*.txt"))
            self.assertEqual(read_yolo_label(generated_label)[0].class_id, 1)

    def test_create_dataset_duplicate_mode_copies_source_pair(self) -> None:
        """Duplicate mode creates new stems without image or label transforms."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            src = root / "src"
            dst = root / "dst"
            self._write_data_yaml(src, ["class-zero"])
            self._make_split(src, "train", {0: 1})
            self._make_split(src, "val", {0: 2})

            summary = create_dataset(
                src_root=src,
                dst_root=dst,
                train_target_per_class=2,
                val_cap_per_class=1,
                seed=42,
                config=build_augmentation_config(GenerationMode.DUPLICATE),
                generation_mode=GenerationMode.DUPLICATE,
            )

            self.assertEqual(summary.generation_mode, GenerationMode.DUPLICATE)
            generated_image = next((dst / "train" / "images").glob("*_aug_c00_*.jpg"))
            generated_label = dst / "train" / "labels" / f"{generated_image.stem}.txt"
            source_image = src / "train" / "images" / "train_c0_000.jpg"
            source_label = src / "train" / "labels" / "train_c0_000.txt"
            self.assertEqual(generated_image.read_bytes(), source_image.read_bytes())
            self.assertEqual(generated_label.read_text(), source_label.read_text())

    def _write_data_yaml(self, root: Path, names: list[str]) -> None:
        root.mkdir(parents=True, exist_ok=True)
        lines = [
            f"path: {root.as_posix()}",
            "train: train/images",
            "val: val/images",
            f"nc: {len(names)}",
            "names:",
            *[f"- {name}" for name in names],
            "",
        ]
        (root / "data.yaml").write_text("\n".join(lines), encoding="utf-8")

    def _make_split(self, root: Path, split: str, counts: dict[int, int]) -> None:
        image_dir = root / split / "images"
        label_dir = root / split / "labels"
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)
        for class_id, count in counts.items():
            for index in range(count):
                stem = f"{split}_c{class_id}_{index:03d}"
                color = (80 + class_id * 40, 120, 160)
                Image.new("RGB", (64, 64), color).save(image_dir / f"{stem}.jpg")
                label = YoloBox(
                    class_id=class_id,
                    x_center=0.5,
                    y_center=0.5,
                    width=0.45,
                    height=0.45,
                )
                (label_dir / f"{stem}.txt").write_text(
                    f"{label.to_label_line()}\n", encoding="utf-8"
                )


class LabelCollectionTest(unittest.TestCase):
    """Checks for class distribution helpers."""

    def test_collect_stems_by_class_includes_all_class_ids(self) -> None:
        """The result contains empty lists for classes that do not appear."""
        with tempfile.TemporaryDirectory() as temp_dir:
            labels = Path(temp_dir)
            (labels / "a.txt").write_text("1 0.5 0.5 0.2 0.2\n", encoding="utf-8")

            result = collect_stems_by_class(labels, num_classes=3)

            self.assertEqual(result[0], [])
            self.assertEqual(result[1], ["a"])
            self.assertEqual(result[2], [])


if __name__ == "__main__":
    unittest.main()
