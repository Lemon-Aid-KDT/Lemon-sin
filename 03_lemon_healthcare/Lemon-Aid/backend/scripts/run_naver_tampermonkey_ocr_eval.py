"""Run provider-specific OCR observations for Naver Tampermonkey manifests.

This is a thin operator wrapper around ``collect_supplement_ocr_observations``.
It keeps live external provider execution explicit and does not print secrets
or raw OCR text.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

BACKEND_ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = BACKEND_ROOT / "scripts" / "collect_supplement_ocr_observations.py"
EVALUATOR = BACKEND_ROOT / "scripts" / "evaluate_naver_tampermonkey_ocr.py"
NUTRITION_BACKEND_ROOT = BACKEND_ROOT / "Nutrition-backend"
OBSERVATION_FILENAME = "supplement-ocr-observations.jsonl"

ProviderAlias = Literal["paddleocr", "clova", "google_vision"]

RAW_FORBIDDEN_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "image_bytes",
        "ocr_text",
        "provider_payload",
        "raw_image",
        "raw_model_response",
        "raw_ocr_text",
        "raw_provider_payload",
        "request_headers",
        "service_key",
    }
)


@dataclass(frozen=True)
class ProviderRun:
    """One provider collector invocation plan.

    Args:
        alias: User-facing provider alias.
        provider_id: Collector provider id.
        output_dir: Provider output directory.
        python_executable: Python executable used for the collector subprocess.
        command: Redacted command arguments.
        env_overrides: Non-secret environment overrides used for opt-in.
    """

    alias: ProviderAlias
    provider_id: str
    output_dir: Path
    python_executable: Path
    command: tuple[str, ...]
    env_overrides: dict[str, str]

    def redacted(self) -> dict[str, object]:
        """Return a JSON-safe, non-secret run description."""
        return {
            "alias": self.alias,
            "provider_id": self.provider_id,
            "output_dir": str(self.output_dir),
            "python_executable": str(self.python_executable),
            "command": list(self.command),
            "env_overrides": dict(sorted(self.env_overrides.items())),
        }


@dataclass(frozen=True)
class ProviderExecutionSummary:
    """Provider execution result with resume accounting.

    Args:
        completed_runs: Runs available for evaluation.
        executed_runs: Runs executed in this invocation.
        resumed_runs: Runs reused from complete prior outputs.
    """

    completed_runs: list[ProviderRun]
    executed_runs: list[ProviderRun]
    resumed_runs: list[ProviderRun]


PROVIDER_CONFIG: dict[ProviderAlias, tuple[str, dict[str, str], bool]] = {
    "paddleocr": (
        "paddleocr_local",
        {"RUN_PADDLEOCR_PROBE": "1", "ENABLE_LOCAL_OCR": "true"},
        False,
    ),
    "clova": (
        "clova_ocr",
        {"RUN_CLOVA_OCR_LIVE_SMOKE": "1", "ALLOW_EXTERNAL_OCR": "true"},
        True,
    ),
    "google_vision": (
        "google_vision_document",
        {"RUN_GOOGLE_VISION_SMOKE": "1", "ALLOW_EXTERNAL_OCR": "true"},
        True,
    ),
}


def main() -> None:
    """Run provider collector commands from CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--env-file", type=Path, default=None)
    parser.add_argument(
        "--python-executable",
        type=Path,
        default=Path(sys.executable),
        help=(
            "Python executable used for collector subprocesses. Use this when "
            "PaddleOCR is installed in a dedicated OCR venv."
        ),
    )
    parser.add_argument(
        "--providers",
        default="paddleocr",
        help="Comma-separated aliases: paddleocr,clova,google_vision.",
    )
    parser.add_argument("--llm-parse", action="store_true")
    parser.add_argument("--allow-external-providers", action="store_true")
    parser.add_argument("--allow-review-external", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse complete provider observation JSONL outputs instead of rerunning collectors.",
    )
    parser.add_argument("--skip-evaluate", action="store_true")
    args = parser.parse_args()

    aliases = parse_provider_aliases(args.providers)
    runs = build_provider_runs(
        manifest_path=args.manifest,
        output_root=args.output_root,
        providers=aliases,
        env_file=args.env_file,
        python_executable=args.python_executable,
        llm_parse=args.llm_parse,
        allow_external_providers=args.allow_external_providers,
        allow_review_external=args.allow_review_external,
    )
    if args.dry_run:
        print(json.dumps({"runs": [run.redacted() for run in runs]}, ensure_ascii=False, indent=2))
        return

    execution = run_provider_evaluations(
        runs,
        resume=args.resume,
        manifest_rows=_read_manifest_rows(args.manifest),
    )
    summary: dict[str, object] = {
        "completed_runs": [run.redacted() for run in execution.completed_runs],
        "executed_runs": [run.redacted() for run in execution.executed_runs],
        "resumed_runs": [run.redacted() for run in execution.resumed_runs],
    }
    if execution.completed_runs and not args.skip_evaluate:
        report = run_comparison_report(
            manifest_path=args.manifest,
            output_root=args.output_root,
            observation_dirs=[run.output_dir for run in execution.completed_runs],
        )
        summary["report"] = report
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def parse_provider_aliases(value: str) -> tuple[ProviderAlias, ...]:
    """Parse comma-separated provider aliases.

    Args:
        value: CLI provider alias list.

    Returns:
        Provider aliases.

    Raises:
        ValueError: If an alias is unsupported.
    """
    aliases: list[ProviderAlias] = []
    for item in value.split(","):
        alias = item.strip()
        if not alias:
            continue
        if alias not in PROVIDER_CONFIG:
            raise ValueError(f"Unsupported provider alias: {alias}")
        aliases.append(alias)  # type: ignore[arg-type]
    if not aliases:
        raise ValueError("At least one provider is required.")
    return tuple(aliases)


def build_provider_runs(
    *,
    manifest_path: Path,
    output_root: Path,
    providers: Sequence[ProviderAlias],
    env_file: Path | None,
    python_executable: Path,
    llm_parse: bool,
    allow_external_providers: bool,
    allow_review_external: bool,
) -> list[ProviderRun]:
    """Build collector invocation plans with external-transfer guardrails.

    Args:
        manifest_path: Redacted OCR manifest.
        output_root: Root directory for provider output folders.
        providers: Provider aliases to run.
        env_file: Optional dotenv file passed to the collector.
        python_executable: Python executable for collector subprocesses.
        llm_parse: Whether to opt into local Ollama parser handoff.
        allow_external_providers: Whether CLOVA/Google Vision may run.
        allow_review_external: Whether review images may be sent externally.

    Returns:
        Provider run plans.

    Raises:
        ValueError: If external provider policy is violated.
    """
    manifest_rows = _read_manifest_rows(manifest_path)
    has_review_rows = any(row.get("section") == "review" for row in manifest_rows)
    runs: list[ProviderRun] = []
    for alias in providers:
        provider_id, env_overrides, external = PROVIDER_CONFIG[alias]
        if external and not allow_external_providers:
            raise ValueError("External providers require --allow-external-providers.")
        if external and has_review_rows and not allow_review_external:
            raise ValueError("Review image external transfer requires --allow-review-external.")
        if external:
            _validate_manifest_external_transfer(manifest_rows)
        output_dir = output_root / f"{alias}-observations"
        command = _collector_command(
            manifest_path=manifest_path,
            output_dir=output_dir,
            provider_id=provider_id,
            env_file=env_file,
            python_executable=python_executable,
            llm_parse=llm_parse,
        )
        runs.append(
            ProviderRun(
                alias=alias,
                provider_id=provider_id,
                output_dir=output_dir,
                python_executable=python_executable,
                command=tuple(command),
                env_overrides=dict(env_overrides),
            )
        )
    return runs


def run_provider_evaluations(
    runs: Sequence[ProviderRun],
    *,
    resume: bool = False,
    manifest_rows: Sequence[dict[str, object]] = (),
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> ProviderExecutionSummary:
    """Execute provider collector commands sequentially.

    Args:
        runs: Provider run plans.
        resume: Whether complete previous outputs may be reused.
        manifest_rows: Manifest rows used to verify complete prior outputs.
        runner: Injectable subprocess runner for tests.

    Returns:
        Provider execution summary.
    """
    completed: list[ProviderRun] = []
    executed: list[ProviderRun] = []
    resumed: list[ProviderRun] = []
    for run in runs:
        if resume and _provider_output_complete(run=run, manifest_rows=manifest_rows):
            completed.append(run)
            resumed.append(run)
            continue
        env = os.environ.copy()
        env["PYTHONPATH"] = str(NUTRITION_BACKEND_ROOT)
        env.update(run.env_overrides)
        runner(
            list(run.command),
            check=True,
            cwd=str(BACKEND_ROOT.parent),
            env=env,
            text=True,
        )
        completed.append(run)
        executed.append(run)
    return ProviderExecutionSummary(
        completed_runs=completed,
        executed_runs=executed,
        resumed_runs=resumed,
    )


def run_comparison_report(
    *,
    manifest_path: Path,
    output_root: Path,
    observation_dirs: Sequence[Path],
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    """Run the Naver Tampermonkey evaluator over provider output dirs.

    Args:
        manifest_path: Redacted manifest path.
        output_root: Output root for the comparison report.
        observation_dirs: Provider observation directories.
        runner: Injectable subprocess runner for tests.

    Returns:
        Redacted report path summary.
    """
    command = [
        sys.executable,
        str(EVALUATOR),
        "--manifest",
        str(manifest_path),
        "--output-dir",
        str(output_root),
    ]
    for directory in observation_dirs:
        command.extend(["--observation-dir", str(directory)])
    runner(command, check=True, cwd=str(BACKEND_ROOT.parent), text=True)
    return {
        "json": str(output_root / "naver-ocr-provider-comparison.json"),
        "markdown": str(output_root / "naver-ocr-provider-comparison.md"),
    }


def _collector_command(
    *,
    manifest_path: Path,
    output_dir: Path,
    provider_id: str,
    env_file: Path | None,
    python_executable: Path,
    llm_parse: bool,
) -> list[str]:
    """Build a collector command without embedding secrets."""
    command = [
        str(python_executable),
        str(COLLECTOR),
        "--manifest",
        str(manifest_path),
        "--output-dir",
        str(output_dir),
        "--providers",
        provider_id,
    ]
    if env_file is not None:
        command.extend(["--env-file", str(env_file)])
    if llm_parse:
        command.append("--llm-parse")
    return command


def _provider_output_complete(
    *,
    run: ProviderRun,
    manifest_rows: Sequence[dict[str, object]],
) -> bool:
    """Return whether a previous provider output fully covers the manifest.

    Completed and error rows both count as terminal outputs. ``not_run`` rows do
    not, because they usually indicate a guard or environment mismatch.
    """
    expected_fixture_ids = {
        str(row["fixture_id"]) for row in manifest_rows if isinstance(row.get("fixture_id"), str)
    }
    if not expected_fixture_ids:
        return False
    path = run.output_dir / OBSERVATION_FILENAME
    if not path.is_file():
        return False

    try:
        seen_fixture_ids = _completed_output_fixture_ids(path=path, provider_id=run.provider_id)
    except (OSError, ValueError, json.JSONDecodeError):
        return False

    return expected_fixture_ids.issubset(seen_fixture_ids)


def _completed_output_fixture_ids(*, path: Path, provider_id: str) -> set[str]:
    """Return terminal fixture ids from one provider observation JSONL."""
    seen_fixture_ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError("Observation row must be an object.")
        _reject_raw_fields(row)
        if row.get("provider") != provider_id:
            raise ValueError("Observation row provider mismatch.")
        fixture_id = row.get("fixture_id")
        status = row.get("status")
        if not isinstance(fixture_id, str) or not isinstance(status, str):
            raise ValueError("Observation row is missing fixture_id or status.")
        if status == "not_run":
            raise ValueError("Observation row is not terminal.")
        seen_fixture_ids.add(fixture_id)
    return seen_fixture_ids


def _read_manifest_rows(path: Path) -> list[dict[str, object]]:
    """Read JSONL or JSON manifest rows and reject raw fields."""
    text = path.read_text(encoding="utf-8")
    rows: list[dict[str, object]]
    if path.suffix == ".jsonl":
        rows = [
            json.loads(line)
            for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
    else:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and isinstance(parsed.get("cases"), list):
            rows = [item for item in parsed["cases"] if isinstance(item, dict)]
        elif isinstance(parsed, list):
            rows = [item for item in parsed if isinstance(item, dict)]
        else:
            raise ValueError("Manifest must be JSONL, a JSON list, or an object with cases.")
    for row in rows:
        _reject_raw_fields(row)
    return rows


def _validate_manifest_external_transfer(rows: Sequence[dict[str, object]]) -> None:
    """Require explicit row-level external transfer eligibility."""
    for row in rows:
        if row.get("contains_personal_data") is not False:
            raise ValueError("External provider rows require contains_personal_data=false.")
        if row.get("external_transfer_allowed") is not True:
            raise ValueError("External provider rows require external_transfer_allowed=true.")


def _reject_raw_fields(value: object) -> None:
    """Reject raw OCR/image/provider/model fields before running providers."""
    if isinstance(value, dict):
        forbidden = RAW_FORBIDDEN_KEYS.intersection(str(key).lower() for key in value)
        if forbidden:
            raise ValueError(f"Payload contains forbidden raw field(s): {sorted(forbidden)}")
        for nested in value.values():
            _reject_raw_fields(nested)
    elif isinstance(value, list):
        for item in value:
            _reject_raw_fields(item)


if __name__ == "__main__":
    main()
