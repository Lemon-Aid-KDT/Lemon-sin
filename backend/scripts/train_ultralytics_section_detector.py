"""Train a supplement section detector with Ultralytics YOLO.

This script is intentionally small so it can be copied to the A100 worker
directory with the materialized dataset. It uses the official Ultralytics
Python API and keeps all run outputs under the caller-provided project
directory.

References:
    https://docs.ultralytics.com/modes/train/
    https://docs.ultralytics.com/datasets/detect/
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Optional argument list for tests.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--imgsz", type=int, default=1280)
    parser.add_argument(
        "--batch",
        default="auto",
        help="'auto' maps to Ultralytics batch=-1 auto 60%% GPU memory mode.",
    )
    parser.add_argument("--device", default="0")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--exist-ok", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run Ultralytics training.

    Args:
        argv: Optional argument list for tests.
    """
    args = parse_args(argv)
    run_training(
        data=args.data,
        model=args.model,
        project=args.project,
        name=args.name,
        epochs=args.epochs,
        patience=args.patience,
        imgsz=args.imgsz,
        batch=_parse_batch(args.batch),
        device=args.device,
        workers=args.workers,
        exist_ok=args.exist_ok,
    )


def run_training(
    *,
    data: Path,
    model: str,
    project: Path,
    name: str,
    epochs: int,
    patience: int,
    imgsz: int,
    batch: int | float,
    device: str,
    workers: int,
    exist_ok: bool,
) -> None:
    """Train one YOLO detector run.

    Args:
        data: Ultralytics detect dataset YAML path.
        model: Model checkpoint or YAML name, such as ``yolov8s.pt``.
        project: Output project directory.
        name: Run name inside the project directory.
        epochs: Maximum epoch count.
        patience: Early-stop patience in epochs without metric improvement.
        imgsz: Training image size.
        batch: Batch setting. ``-1`` enables Ultralytics auto-batch mode.
        device: Device argument accepted by Ultralytics, e.g. ``"0"``.
        workers: DataLoader worker count.
        exist_ok: Whether Ultralytics can reuse an existing run directory.

    Raises:
        RuntimeError: Propagated by Ultralytics if training fails.
    """
    from ultralytics import YOLO  # noqa: PLC0415

    start_payload: dict[str, Any] = {
        "event": "SECTION_YOLO_TRAIN_START",
        "created_at": datetime.now(UTC).isoformat(),
        "model": model,
        "data": str(data),
        "project": str(project),
        "name": name,
        "epochs": epochs,
        "patience": patience,
        "imgsz": imgsz,
        "batch": batch,
        "device": device,
        "workers": workers,
        "source_doc_urls": [
            "https://docs.ultralytics.com/modes/train/",
            "https://docs.ultralytics.com/datasets/detect/",
        ],
    }
    print(json.dumps(start_payload, ensure_ascii=False, sort_keys=True), flush=True)
    YOLO(model).train(
        data=str(data),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        project=str(project),
        name=name,
        patience=patience,
        exist_ok=exist_ok,
        verbose=True,
        workers=workers,
        cache=False,
        save=True,
        plots=True,
    )
    print(
        json.dumps(
            {
                "event": "SECTION_YOLO_TRAIN_DONE",
                "created_at": datetime.now(UTC).isoformat(),
                "model": model,
                "name": name,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        flush=True,
    )


def _parse_batch(value: str) -> int | float:
    """Parse Ultralytics batch setting.

    Args:
        value: CLI value. ``auto`` maps to ``-1``.

    Returns:
        Integer or float batch value accepted by Ultralytics.

    Raises:
        ValueError: If the batch value is not numeric or ``auto``.
    """
    normalized = value.strip().lower()
    if normalized == "auto":
        return -1
    try:
        if "." in normalized:
            return float(normalized)
        return int(normalized)
    except ValueError as exc:
        raise ValueError("batch must be 'auto', an integer, or a float fraction.") from exc


if __name__ == "__main__":
    main()
