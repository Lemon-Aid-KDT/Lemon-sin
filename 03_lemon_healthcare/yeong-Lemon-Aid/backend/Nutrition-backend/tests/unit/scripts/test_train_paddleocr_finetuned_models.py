"""Tests for the PaddleOCR fine-tuning training runner."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.train_paddleocr_finetuned_models import (
    PaddleOCRTrainingRunnerError,
    build_training_plan,
    resolve_single_config,
    training_plan_to_dict,
)


def test_build_training_plan_dry_run_validates_source_dataset_and_commands(tmp_path: Path) -> None:
    """Verify dry-run prints commands without starting training."""
    source_dir = _write_source_checkout(tmp_path)
    dataset_dir = _write_exported_dataset(tmp_path)

    plan = build_training_plan(
        paddleocr_source_dir=source_dir,
        dataset_dir=dataset_dir,
        dry_run=True,
    )
    payload = training_plan_to_dict(plan)

    assert payload["dry_run"] is True
    assert payload["starts_training"] is False
    assert len(plan.tasks) == 2
    assert plan.tasks[0].model_name == "PP-OCRv5_server_det"
    assert plan.tasks[1].model_name == "korean_PP-OCRv5_mobile_rec"
    assert str(source_dir / "tools" / "train.py") in plan.tasks[0].train_command
    assert "-c" in plan.tasks[0].train_command
    assert str(dataset_dir / "det" / "train.txt") in " ".join(plan.tasks[0].train_command)
    assert str(dataset_dir / "rec" / "val.txt") in " ".join(plan.tasks[1].eval_command)
    det_command = " ".join(plan.tasks[0].train_command)
    rec_command = " ".join(plan.tasks[1].train_command)
    assert "Global.use_gpu=False" in det_command
    assert "Global.distributed=False" in det_command
    assert "Train.loader.batch_size_per_card=1" in det_command
    assert "Train.loader.num_workers=0" in det_command
    assert "Train.sampler.first_bs=4" in rec_command
    assert "Eval.loader.batch_size_per_card=4" in rec_command
    assert "Global.use_gpu=False" in " ".join(plan.tasks[0].eval_command)
    assert "Global.distributed=False" in " ".join(plan.tasks[1].export_command)


def test_resolve_single_config_fails_fast_on_missing_or_ambiguous_config(tmp_path: Path) -> None:
    """Verify source config matching is exact enough for operator safety."""
    source_dir = _write_source_checkout(tmp_path)

    with pytest.raises(PaddleOCRTrainingRunnerError, match="No PaddleOCR config"):
        resolve_single_config(source_dir, "missing_model")

    custom_a = source_dir / "configs" / "rec" / "custom_model.yml"
    custom_b = source_dir / "configs" / "det" / "custom_model.yml"
    custom_a.write_text("Global: {}\n", encoding="utf-8")
    custom_b.write_text("Global: {}\n", encoding="utf-8")
    with pytest.raises(PaddleOCRTrainingRunnerError, match="Multiple PaddleOCR configs"):
        resolve_single_config(source_dir, "custom_model")


def test_resolve_default_config_requires_official_relative_path(tmp_path: Path) -> None:
    """Verify default PaddleOCR configs are checked at the official source paths."""
    source_dir = _write_source_checkout(tmp_path)
    default_rec_config = (
        source_dir
        / "configs"
        / "rec"
        / "PP-OCRv5"
        / "multi_language"
        / "korean_PP-OCRv5_mobile_rec.yml"
    )
    default_rec_config.unlink()

    with pytest.raises(PaddleOCRTrainingRunnerError, match="Expected PaddleOCR config"):
        resolve_single_config(source_dir, "korean_PP-OCRv5_mobile_rec")


def test_build_training_plan_rejects_missing_exported_label_files(tmp_path: Path) -> None:
    """Verify the runner does not start from incomplete exported datasets."""
    source_dir = _write_source_checkout(tmp_path)
    dataset_dir = tmp_path / "dataset"
    (dataset_dir / "det").mkdir(parents=True)

    with pytest.raises(PaddleOCRTrainingRunnerError, match="missing required label"):
        build_training_plan(
            paddleocr_source_dir=source_dir,
            dataset_dir=dataset_dir,
            dry_run=True,
        )


def _write_source_checkout(tmp_path: Path) -> Path:
    source_dir = tmp_path / "PaddleOCR"
    tools_dir = source_dir / "tools"
    tools_dir.mkdir(parents=True)
    for name in ("train.py", "eval.py", "export_model.py"):
        (tools_dir / name).write_text("print('stub')\n", encoding="utf-8")
    det_config = source_dir / "configs" / "det" / "PP-OCRv5" / "PP-OCRv5_server_det.yml"
    rec_config = (
        source_dir
        / "configs"
        / "rec"
        / "PP-OCRv5"
        / "multi_language"
        / "korean_PP-OCRv5_mobile_rec.yml"
    )
    det_config.parent.mkdir(parents=True)
    rec_config.parent.mkdir(parents=True)
    det_config.write_text("Global: {}\n", encoding="utf-8")
    rec_config.write_text("Global: {}\n", encoding="utf-8")
    return source_dir


def _write_exported_dataset(tmp_path: Path) -> Path:
    dataset_dir = tmp_path / "dataset"
    for task in ("det", "rec"):
        task_dir = dataset_dir / task
        task_dir.mkdir(parents=True)
        (task_dir / "train.txt").write_text("images/train/a.png\tlabel\n", encoding="utf-8")
        (task_dir / "val.txt").write_text("images/val/a.png\tlabel\n", encoding="utf-8")
    return dataset_dir
