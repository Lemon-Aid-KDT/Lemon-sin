"""Evaluate and optionally apply a model candidate promotion gate."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
NUTRITION_BACKEND_ROOT = BACKEND_ROOT / "Nutrition-backend"
if str(NUTRITION_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(NUTRITION_BACKEND_ROOT))

from src.db.session import get_sessionmaker  # noqa: E402
from src.learning.retraining import (  # noqa: E402
    MetricGateRule,
    ModelPromotionGateError,
    evaluate_model_promotion_gate,
)
from src.models.db.retraining import (  # noqa: E402
    ModelEvalResult,
    ModelRegistryEntry,
    ModelTrainingRun,
)

SUMMARY_SCHEMA_VERSION = "model-promotion-cli-summary-v1"
ALLOWED_COMPARATORS = frozenset({">=", ">", "<=", "<"})
OPERATOR_HASH_LENGTH = 64


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments.

    Args:
        argv: Optional argument list for tests.

    Returns:
        Parsed CLI namespace.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-run-id", required=True, type=UUID)
    parser.add_argument("--model-id", required=True, type=UUID)
    parser.add_argument(
        "--metric-rule",
        action="append",
        default=[],
        nargs=3,
        metavar=("METRIC", "COMPARATOR", "THRESHOLD"),
        help="Required metric gate, for example: --metric-rule cer '<=' 0.10",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist staging promotion only when the gate passes.",
    )
    parser.add_argument(
        "--approved-by-hash",
        default=None,
        help="Optional 64-character operator hash stored only with --apply.",
    )
    return parser.parse_args(argv)


async def run_cli(argv: list[str] | None = None) -> int:
    """Parse arguments, evaluate the gate, and print a sanitized summary.

    Args:
        argv: Optional argument list for tests.

    Returns:
        Process exit code.
    """
    args = parse_args(argv)
    try:
        metric_rules = [_parse_metric_rule(rule) for rule in args.metric_rule]
        summary = await promote_model_candidate(
            training_run_id=args.training_run_id,
            model_id=args.model_id,
            metric_rules=metric_rules,
            apply=args.apply,
            approved_by_hash=args.approved_by_hash,
        )
    except (InvalidOperation, ModelPromotionGateError, ValueError) as exc:
        summary = _error_summary(error=exc)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 1

    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if summary["allowed"] is True else 1


async def promote_model_candidate(
    *,
    training_run_id: UUID,
    model_id: UUID,
    metric_rules: list[MetricGateRule],
    apply: bool,
    approved_by_hash: str | None = None,
) -> dict[str, object]:
    """Evaluate and optionally persist a candidate model promotion.

    Args:
        training_run_id: Training run that produced the model.
        model_id: Candidate model registry id.
        metric_rules: Required metric gate rules.
        apply: Whether to persist the staging promotion when the gate passes.
        approved_by_hash: Optional operator hash stored only with apply.

    Returns:
        Sanitized promotion summary.

    Raises:
        ValueError: If required rows are missing or operator hash is invalid.
        ModelPromotionGateError: If lineage or metric rules are invalid.
    """
    if approved_by_hash is not None and len(approved_by_hash) != OPERATOR_HASH_LENGTH:
        raise ValueError("approved_by_hash must be 64 characters when provided.")

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        training_run = await session.get(ModelTrainingRun, training_run_id)
        model = await session.get(ModelRegistryEntry, model_id)
        if training_run is None:
            raise ValueError("Model training run was not found.")
        if model is None:
            raise ValueError("Model registry entry was not found.")

        eval_results = await _load_eval_results(session=session, model_id=model_id)
        gate_snapshot = evaluate_model_promotion_gate(
            training_run=training_run,
            model=model,
            eval_results=eval_results,
            required_metrics=metric_rules,
        )
        applied = False
        if apply and gate_snapshot["allowed"] is True:
            model.deployment_status = "staging"
            model.metric_gate_snapshot = gate_snapshot
            model.approved_by_hash = approved_by_hash
            model.approved_at = datetime.now(UTC)
            training_run.status = "approved_for_deploy"
            await session.commit()
            applied = True

    return _summary_from_gate(gate_snapshot=gate_snapshot, applied=applied)


async def _load_eval_results(
    *,
    session: Any,
    model_id: UUID,
) -> list[ModelEvalResult]:
    """Return persisted evaluation metric rows for one model.

    Args:
        session: Async DB session.
        model_id: Model registry id.

    Returns:
        Evaluation result rows.
    """
    statement = (
        select(ModelEvalResult)
        .where(ModelEvalResult.model_id == model_id)
        .order_by(ModelEvalResult.metric_name.asc(), ModelEvalResult.id.asc())
    )
    return list((await session.scalars(statement)).all())


def _parse_metric_rule(raw_rule: list[str]) -> MetricGateRule:
    """Parse one CLI metric rule.

    Args:
        raw_rule: ``[metric_name, comparator, threshold]`` from argparse.

    Returns:
        Metric gate rule.

    Raises:
        ValueError: If the comparator is unsupported.
        InvalidOperation: If the threshold is not decimal-compatible.
    """
    metric_name, comparator, raw_threshold = raw_rule
    if comparator not in ALLOWED_COMPARATORS:
        raise ValueError("Unsupported metric gate comparator.")
    return MetricGateRule(
        metric_name=metric_name,
        comparator=comparator,
        threshold=Decimal(raw_threshold),
    )


def _summary_from_gate(
    *,
    gate_snapshot: dict[str, Any],
    applied: bool,
) -> dict[str, object]:
    """Return a redacted promotion summary.

    Args:
        gate_snapshot: Result from ``evaluate_model_promotion_gate``.
        applied: Whether DB state was updated.

    Returns:
        Summary without artifact refs, storage refs, operator hash, or raw payloads.
    """
    rules = gate_snapshot.get("rules")
    rule_count = len(rules) if isinstance(rules, list) else 0
    passed_rule_count = (
        sum(1 for rule in rules if isinstance(rule, dict) and rule.get("passed") is True)
        if isinstance(rules, list)
        else 0
    )
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": "ok",
        "allowed": gate_snapshot["allowed"],
        "applied": applied,
        "reason": gate_snapshot["reason"],
        "model_id": gate_snapshot["model_id"],
        "training_run_id": gate_snapshot["training_run_id"],
        "rule_count": rule_count,
        "passed_rule_count": passed_rule_count,
        "artifact_ref_stored": False,
        "operator_hash_printed": False,
        "raw_eval_payload_stored": False,
    }


def _error_summary(*, error: BaseException) -> dict[str, object]:
    """Return a redacted error summary.

    Args:
        error: Raised exception.

    Returns:
        Summary with only the exception class.
    """
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": "error",
        "error_type": type(error).__name__,
        "allowed": False,
        "applied": False,
        "artifact_ref_stored": False,
        "operator_hash_printed": False,
        "raw_eval_payload_stored": False,
    }


def main() -> None:
    """Run the CLI entrypoint."""
    raise SystemExit(asyncio.run(run_cli()))


if __name__ == "__main__":
    main()
