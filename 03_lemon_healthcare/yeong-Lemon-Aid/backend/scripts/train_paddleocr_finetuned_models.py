"""Build or run local PaddleOCR fine-tuning commands.

The runner requires an existing PaddleOCR source checkout. It never clones code
or downloads weights automatically. Use ``--dry-run`` first on Local Mac CPU to
verify source files, dataset labels, config resolution, and output paths before
starting a long training job.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

BACKEND_ROOT = Path(__file__).resolve().parents[1]
NUTRITION_BACKEND_ROOT = BACKEND_ROOT / "Nutrition-backend"
if str(NUTRITION_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(NUTRITION_BACKEND_ROOT))

TaskName = Literal["det", "rec"]
DEFAULT_DET_MODEL_NAME = "PP-OCRv5_server_det"
DEFAULT_REC_MODEL_NAME = "korean_PP-OCRv5_mobile_rec"
DEFAULT_CONFIG_RELATIVE_PATHS = {
    DEFAULT_DET_MODEL_NAME: Path("configs/det/PP-OCRv5/PP-OCRv5_server_det.yml"),
    DEFAULT_REC_MODEL_NAME: Path(
        "configs/rec/PP-OCRv5/multi_language/korean_PP-OCRv5_mobile_rec.yml"
    ),
}
LOCAL_MAC_CPU_COMMAND_OVERRIDES = (
    "Global.use_gpu=False",
    "Global.distributed=False",
)
LOCAL_MAC_CPU_TASK_OVERRIDES = {
    "det": (
        "Train.loader.batch_size_per_card=1",
        "Train.loader.num_workers=0",
        "Eval.loader.batch_size_per_card=1",
        "Eval.loader.num_workers=0",
    ),
    "rec": (
        "Train.sampler.first_bs=4",
        "Train.loader.batch_size_per_card=4",
        "Train.loader.num_workers=0",
        "Eval.loader.batch_size_per_card=4",
        "Eval.loader.num_workers=0",
    ),
}


class PaddleOCRTrainingRunnerError(ValueError):
    """Raised when a PaddleOCR fine-tuning command plan is invalid."""


@dataclass(frozen=True)
class PaddleOCRTaskPlan:
    """Commands for one PaddleOCR fine-tuning task.

    Attributes:
        task: PaddleOCR task name.
        model_name: PaddleOCR model/config search name.
        config_path: Resolved source config path.
        train_label_path: Training label file.
        val_label_path: Validation label file.
        output_dir: Private training output directory.
        export_dir: Private inference export output directory.
        train_command: Training command.
        eval_command: Evaluation command.
        export_command: Export command.
    """

    task: TaskName
    model_name: str
    config_path: str
    train_label_path: str
    val_label_path: str
    output_dir: str
    export_dir: str
    train_command: list[str]
    eval_command: list[str]
    export_command: list[str]


@dataclass(frozen=True)
class PaddleOCRTrainingPlan:
    """Complete Detection+Recognition training plan.

    Attributes:
        generated_at: Plan timestamp.
        paddleocr_source_dir: PaddleOCR source checkout path.
        dataset_dir: Exported private dataset path.
        dry_run: Whether commands should only be printed.
        tasks: Task command plans.
        official_source_required: Whether a real PaddleOCR source checkout is required.
    """

    generated_at: str
    paddleocr_source_dir: str
    dataset_dir: str
    dry_run: bool
    tasks: list[PaddleOCRTaskPlan]
    official_source_required: bool = True


def main() -> None:
    """Run or print the PaddleOCR fine-tuning plan."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paddleocr-source-dir", required=True, type=Path)
    parser.add_argument("--dataset-dir", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--det-model-name", default=DEFAULT_DET_MODEL_NAME)
    parser.add_argument("--rec-model-name", default=DEFAULT_REC_MODEL_NAME)
    parser.add_argument("--det-pretrained-model", type=Path)
    parser.add_argument("--rec-pretrained-model", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    plan = build_training_plan(
        paddleocr_source_dir=args.paddleocr_source_dir,
        dataset_dir=args.dataset_dir,
        output_dir=args.output_dir,
        det_model_name=args.det_model_name,
        rec_model_name=args.rec_model_name,
        det_pretrained_model=args.det_pretrained_model,
        rec_pretrained_model=args.rec_pretrained_model,
        dry_run=args.dry_run,
    )
    if not args.dry_run:
        run_training_plan(plan)
    print(json.dumps(training_plan_to_dict(plan), ensure_ascii=False, indent=2))


def build_training_plan(
    *,
    paddleocr_source_dir: Path,
    dataset_dir: Path,
    output_dir: Path | None = None,
    det_model_name: str = DEFAULT_DET_MODEL_NAME,
    rec_model_name: str = DEFAULT_REC_MODEL_NAME,
    det_pretrained_model: Path | None = None,
    rec_pretrained_model: Path | None = None,
    dry_run: bool = True,
) -> PaddleOCRTrainingPlan:
    """Build a validated local training plan.

    Args:
        paddleocr_source_dir: Existing PaddleOCR source checkout.
        dataset_dir: Exported dataset directory from the local exporter.
        output_dir: Private training output directory.
        det_model_name: Detection config search name.
        rec_model_name: Recognition config search name.
        det_pretrained_model: Optional local detection pretrained checkpoint.
        rec_pretrained_model: Optional local recognition pretrained checkpoint.
        dry_run: Whether the caller intends to dry-run only.

    Returns:
        Validated training plan.

    Raises:
        PaddleOCRTrainingRunnerError: If required source, config, or dataset files are missing.
    """
    tools = validate_paddleocr_source_dir(paddleocr_source_dir)
    validate_dataset_dir(dataset_dir)
    output_root = output_dir or dataset_dir / "models"
    det_config = resolve_single_config(paddleocr_source_dir, det_model_name)
    rec_config = resolve_single_config(paddleocr_source_dir, rec_model_name)
    tasks = [
        build_task_plan(
            task="det",
            model_name=det_model_name,
            config_path=det_config,
            tools=tools,
            dataset_dir=dataset_dir,
            output_root=output_root,
            pretrained_model=det_pretrained_model,
        ),
        build_task_plan(
            task="rec",
            model_name=rec_model_name,
            config_path=rec_config,
            tools=tools,
            dataset_dir=dataset_dir,
            output_root=output_root,
            pretrained_model=rec_pretrained_model,
        ),
    ]
    return PaddleOCRTrainingPlan(
        generated_at=datetime.now(UTC).isoformat(),
        paddleocr_source_dir=str(paddleocr_source_dir),
        dataset_dir=str(dataset_dir),
        dry_run=dry_run,
        tasks=tasks,
    )


def validate_paddleocr_source_dir(paddleocr_source_dir: Path) -> dict[str, Path]:
    """Validate a PaddleOCR source checkout contains required entry points.

    Args:
        paddleocr_source_dir: Existing PaddleOCR source checkout.

    Returns:
        Mapping of tool names to paths.

    Raises:
        PaddleOCRTrainingRunnerError: If any required entry point is missing.
    """
    required = {
        "train": paddleocr_source_dir / "tools" / "train.py",
        "eval": paddleocr_source_dir / "tools" / "eval.py",
        "export": paddleocr_source_dir / "tools" / "export_model.py",
    }
    missing = [str(path) for path in required.values() if not path.exists()]
    if missing:
        raise PaddleOCRTrainingRunnerError(
            "PaddleOCR source checkout is missing required tool(s): " + ", ".join(missing)
        )
    return {name: path.resolve() for name, path in required.items()}


def validate_dataset_dir(dataset_dir: Path) -> None:
    """Validate exported detection and recognition label files exist.

    Args:
        dataset_dir: Exported private dataset directory.

    Raises:
        PaddleOCRTrainingRunnerError: If expected split label files are missing.
    """
    required = [
        dataset_dir / "det" / "train.txt",
        dataset_dir / "det" / "val.txt",
        dataset_dir / "rec" / "train.txt",
        dataset_dir / "rec" / "val.txt",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise PaddleOCRTrainingRunnerError(
            "Exported dataset is missing required label file(s): " + ", ".join(missing)
        )


def resolve_single_config(paddleocr_source_dir: Path, model_name: str) -> Path:
    """Resolve exactly one PaddleOCR config for a model name.

    Args:
        paddleocr_source_dir: Existing PaddleOCR source checkout.
        model_name: Model/config search name.

    Returns:
        Matching config path.

    Raises:
        PaddleOCRTrainingRunnerError: If no config or multiple configs match.
    """
    expected_relative_path = DEFAULT_CONFIG_RELATIVE_PATHS.get(model_name)
    if expected_relative_path is not None:
        expected_path = paddleocr_source_dir / expected_relative_path
        if not expected_path.exists():
            raise PaddleOCRTrainingRunnerError(
                f"Expected PaddleOCR config not found for {model_name}: {expected_path}"
            )
        return expected_path.resolve()

    patterns = [
        f"configs/**/*{model_name}*.yml",
        f"configs/**/*{model_name}*.yaml",
    ]
    matches: list[Path] = []
    for pattern in patterns:
        matches.extend(paddleocr_source_dir.glob(pattern))
    unique_matches = sorted({path.resolve() for path in matches})
    if not unique_matches:
        raise PaddleOCRTrainingRunnerError(f"No PaddleOCR config matched model name: {model_name}")
    if len(unique_matches) > 1:
        joined = ", ".join(str(path) for path in unique_matches)
        raise PaddleOCRTrainingRunnerError(
            f"Multiple PaddleOCR configs matched {model_name}; choose a more specific name: {joined}"
        )
    return unique_matches[0]


def build_task_plan(
    *,
    task: TaskName,
    model_name: str,
    config_path: Path,
    tools: dict[str, Path],
    dataset_dir: Path,
    output_root: Path,
    pretrained_model: Path | None,
) -> PaddleOCRTaskPlan:
    """Build train/eval/export commands for one PaddleOCR task.

    Args:
        task: det or rec.
        model_name: PaddleOCR model name.
        config_path: Resolved PaddleOCR config.
        tools: Validated PaddleOCR tool paths.
        dataset_dir: Exported private dataset directory.
        output_root: Private output root.
        pretrained_model: Optional local pretrained checkpoint.

    Returns:
        Task command plan.
    """
    task_dataset_dir = dataset_dir / task
    train_label_path = task_dataset_dir / "train.txt"
    val_label_path = task_dataset_dir / "val.txt"
    task_output_dir = output_root / task / "training"
    export_dir = output_root / task / "inference"
    overrides = [
        *LOCAL_MAC_CPU_COMMAND_OVERRIDES,
        *LOCAL_MAC_CPU_TASK_OVERRIDES[task],
        f"Global.save_model_dir={task_output_dir}",
        f"Global.save_inference_dir={export_dir}",
        f"Train.dataset.data_dir={dataset_dir}",
        f"Train.dataset.label_file_list=['{train_label_path}']",
        f"Eval.dataset.data_dir={dataset_dir}",
        f"Eval.dataset.label_file_list=['{val_label_path}']",
    ]
    if pretrained_model is not None:
        if not pretrained_model.exists():
            raise PaddleOCRTrainingRunnerError(
                f"Pretrained model path does not exist: {pretrained_model}"
            )
        overrides.append(f"Global.pretrained_model={pretrained_model}")

    train_command = [
        sys.executable,
        str(tools["train"]),
        "-c",
        str(config_path),
        "-o",
        *overrides,
    ]
    eval_command = [
        sys.executable,
        str(tools["eval"]),
        "-c",
        str(config_path),
        "-o",
        *LOCAL_MAC_CPU_COMMAND_OVERRIDES,
        f"Global.checkpoints={task_output_dir / 'best_accuracy'}",
        f"Eval.dataset.data_dir={dataset_dir}",
        f"Eval.dataset.label_file_list=['{val_label_path}']",
    ]
    export_command = [
        sys.executable,
        str(tools["export"]),
        "-c",
        str(config_path),
        "-o",
        *LOCAL_MAC_CPU_COMMAND_OVERRIDES,
        f"Global.checkpoints={task_output_dir / 'best_accuracy'}",
        f"Global.save_inference_dir={export_dir}",
    ]
    return PaddleOCRTaskPlan(
        task=task,
        model_name=model_name,
        config_path=str(config_path),
        train_label_path=str(train_label_path),
        val_label_path=str(val_label_path),
        output_dir=str(task_output_dir),
        export_dir=str(export_dir),
        train_command=train_command,
        eval_command=eval_command,
        export_command=export_command,
    )


def run_training_plan(plan: PaddleOCRTrainingPlan) -> None:
    """Run train, eval, and export commands sequentially.

    Args:
        plan: Validated training plan.

    Raises:
        subprocess.CalledProcessError: If a PaddleOCR command fails.
    """
    for task in plan.tasks:
        for command in (task.train_command, task.eval_command, task.export_command):
            subprocess.run(command, check=True)


def training_plan_to_dict(plan: PaddleOCRTrainingPlan) -> dict[str, object]:
    """Convert a training plan to JSON-serializable data.

    Args:
        plan: Training plan.

    Returns:
        JSON-serializable plan dictionary.
    """
    payload = asdict(plan)
    payload["starts_training"] = not plan.dry_run
    payload["dry_run_note"] = (
        "Dry-run validates source/config/dataset paths and prints commands only."
        if plan.dry_run
        else "Training commands were executed sequentially."
    )
    payload["metrics_are_predicted"] = False
    return payload


if __name__ == "__main__":
    main()
