"""Launch the A100 section detector training as a detached Windows process.

The launcher is intentionally small and explicit: it checks current free GPU
memory, records the exact training arguments, then spawns the actual Ultralytics
training script in a process group that can survive the SSH session ending.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_BREAKAWAY_FROM_JOB = 0x01000000


def _append_state(state_log: Path, message: str) -> None:
    """Append a timestamped state line for operator-visible A100 monitoring.

    Args:
        state_log: Path to the queue/state log on the A100 workspace.
        message: Single-line status message to append.
    """
    now = datetime.now(timezone.utc).astimezone().isoformat()
    state_log.parent.mkdir(parents=True, exist_ok=True)
    with state_log.open("a", encoding="utf-8") as handle:
        handle.write(f"{now} {message}\n")


def _query_free_gpu_mib() -> int:
    """Return current free GPU memory reported by nvidia-smi.

    Returns:
        Free GPU memory in MiB.

    Raises:
        subprocess.CalledProcessError: If nvidia-smi fails.
        ValueError: If the output cannot be parsed as an integer.
    """
    output = subprocess.check_output(
        [
            "nvidia-smi",
            "--query-gpu=memory.free",
            "--format=csv,noheader,nounits",
        ],
        text=True,
    )
    return int(output.splitlines()[0].strip())


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the detached A100 launcher.

    Returns:
        Parsed argparse namespace.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=r"G:\lemon-aid\section_dataset_v2_panel_pseudo_a100")
    parser.add_argument("--python", default=r"G:\anaconda3\envs\lemonaid_project\python.exe")
    parser.add_argument("--model", default="yolo26s.pt")
    parser.add_argument(
        "--name",
        default="sec_v2_panel_pseudo_a100_yolo26s_300ep_noearly_52g_b070_pyspawn_v2",
    )
    parser.add_argument("--min-free-mib", type=int, default=52_000)
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--patience", type=int, default=0)
    parser.add_argument("--imgsz", type=int, default=1280)
    parser.add_argument("--batch", default="0.70")
    parser.add_argument("--workers", type=int, default=2)
    return parser.parse_args()


def main() -> int:
    """Launch the detached training process.

    Returns:
        Process exit code for the launcher, not the detached trainer.
    """
    args = parse_args()
    base = Path(args.base)
    state_log = base / "queue_keeper.state.log"
    train_script = base / "train_ultralytics_section_detector.py"
    data_yaml = base / "dataset.yaml"
    project = base / "runs"
    log_path = base / f"train_{args.name}.log"
    err_path = base / f"train_{args.name}.err"

    free_mib = _query_free_gpu_mib()
    if free_mib < args.min_free_mib:
        _append_state(
            state_log,
            (
                f"PYSPAWN_WAIT_300_NOEARLY name={args.name} "
                f"reason=insufficient_free_gpu_mib free_mib={free_mib} "
                f"required_mib={args.min_free_mib}"
            ),
        )
        return 3

    cmd = [
        args.python,
        str(train_script),
        "--data",
        str(data_yaml),
        "--model",
        args.model,
        "--project",
        str(project),
        "--name",
        args.name,
        "--epochs",
        str(args.epochs),
        "--patience",
        str(args.patience),
        "--imgsz",
        str(args.imgsz),
        "--batch",
        str(args.batch),
        "--device",
        "0",
        "--workers",
        str(args.workers),
    ]

    _append_state(
        state_log,
        (
            f"PYSPAWN_LAUNCH_300_NOEARLY model={args.model} name={args.name} "
            f"min_free_mib={args.min_free_mib} free_mib={free_mib} "
            f"epochs={args.epochs} patience={args.patience} imgsz={args.imgsz} "
            f"batch={args.batch}"
        ),
    )
    with log_path.open("ab", buffering=0) as stdout, err_path.open("ab", buffering=0) as stderr:
        proc = subprocess.Popen(
            cmd,
            cwd=str(base),
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            close_fds=True,
            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_BREAKAWAY_FROM_JOB,
        )
    _append_state(state_log, f"PYSPAWN_PID_300_NOEARLY name={args.name} pid={proc.pid}")
    time.sleep(8)
    return_code = proc.poll()
    if return_code is not None:
        _append_state(
            state_log,
            f"PYSPAWN_EARLY_EXIT_300_NOEARLY name={args.name} code={return_code}",
        )
        return 4

    print(f"launched pid={proc.pid} name={args.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
