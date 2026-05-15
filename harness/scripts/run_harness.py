"""Run Lemon Aid Agent harness scenarios.

The scenario and config files use JSON-compatible YAML so this script can stay
dependency-free in a fresh checkout.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "harness"


class HarnessError(RuntimeError):
    """Raised when a scenario or fixture is invalid."""


@dataclass(frozen=True)
class StepResult:
    kind: str
    name: str
    status: str
    output: dict[str, Any]


def load_json_compatible_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_fixture(relative_path: str) -> dict[str, Any]:
    return load_json_compatible_yaml(HARNESS / "fixtures" / relative_path)


def has_agent_consent(user: dict[str, Any]) -> bool:
    consent = user.get("consent_state", {})
    return bool(consent.get("health_data") and consent.get("agent_execution"))


def contains_blocked_term(text: str, blocked_terms: list[str]) -> str | None:
    for term in blocked_terms:
        if term in text:
            return term
    return None


def mock_agent_output(
    agent: str,
    user: dict[str, Any],
    analysis: dict[str, Any],
    memory: dict[str, Any],
) -> dict[str, Any]:
    request_id = analysis["request_id"]
    base = {
        "request_id": request_id,
        "agent_name": agent,
        "used_tools": [],
        "latency_ms": 0,
        "cost_usd": 0.0,
        "safety_status": "passed",
    }

    if agent == "personalization":
        base["result"] = {
            "cautions": user["profile"].get("chronic_conditions", []),
            "memory_focus": memory.get("summary_json", {}).get("recent_focus", []),
            "message": "입력 기준으로 주의가 필요할 수 있는 영양 관리 기준을 요약했습니다. 전문가 상담을 권장합니다.",
        }
        return base

    if agent == "evaluation":
        summary = analysis.get("nutrition_summary", {})
        vitamin_d_pct = summary.get("vitamin_d_pct", 125)
        base["result"] = {
            "score": 78,
            "low_nutrients": ["vitamin_d"] if vitamin_d_pct < 50 else [],
            "comment": "권장량 대비 낮은 항목은 참고용으로 확인하고, 복약 중이면 전문가 상담을 권장합니다.",
        }
        return base

    if agent == "chat":
        base["used_tools"] = ["add_reminder"]
        base["result"] = {
            "reply": "알림 등록 예정 내용을 먼저 확인해 주세요. 복약 관련 변경은 전문가 상담을 권장합니다.",
            "intent": "create_reminder_preview",
        }
        return base

    raise HarnessError(f"Unsupported agent: {agent}")


def mock_tool_preview(tool: str, analysis: dict[str, Any]) -> dict[str, Any]:
    if tool == "extract_supplement_facts":
        payload = analysis.get("parsed", {})
    elif tool == "add_reminder":
        payload = {
            "type": "medication",
            "name": "혈압약",
            "time": "08:00",
            "recurrence": "daily",
        }
    else:
        payload = {"tool": tool}

    return {
        "tool_name": tool,
        "preview_payload": payload,
        "requires_approval": True,
        "side_effect_status": "pending",
    }


def run_scenario(
    scenario_path: Path,
    harness_config: dict[str, Any],
    safety_policy: dict[str, Any],
) -> dict[str, Any]:
    scenario = load_json_compatible_yaml(scenario_path)
    user = load_fixture(scenario["user_fixture"])
    analysis = load_fixture(scenario["analysis_fixture"])
    memory = load_fixture(scenario["memory_fixture"])
    expected = scenario["expect"]
    step_results: list[StepResult] = []
    failures: list[str] = []
    blocked = False
    block_reason: str | None = None

    if not has_agent_consent(user):
        blocked = True
        block_reason = "consent_required"
    else:
        for step in scenario["steps"]:
            if step["type"] == "agent":
                agent = step["agent"]
                if agent not in harness_config["agent_names"]:
                    failures.append(f"unsupported_agent:{agent}")
                    continue
                output = mock_agent_output(agent, user, analysis, memory)
                blocked_term = contains_blocked_term(
                    json.dumps(output, ensure_ascii=False),
                    safety_policy["blocked_terms"],
                )
                if blocked_term:
                    failures.append(f"blocked_term:{blocked_term}")
                step_results.append(StepResult("agent", agent, "passed", output))
            elif step["type"] == "tool_preview":
                tool = step["tool"]
                output = mock_tool_preview(tool, analysis)
                step_results.append(StepResult("tool_preview", tool, "passed", output))
            else:
                failures.append(f"unknown_step_type:{step['type']}")

    actual_status = "blocked" if blocked else ("failed" if failures else "passed")
    if actual_status != expected["status"]:
        failures.append(f"status:{actual_status}!={expected['status']}")
    if expected.get("block_reason") and block_reason != expected["block_reason"]:
        failures.append(f"block_reason:{block_reason}!={expected['block_reason']}")

    agents = [step.name for step in step_results if step.kind == "agent"]
    tools = [step.name for step in step_results if step.kind == "tool_preview"]

    for agent in expected.get("required_agents", []):
        if agent not in agents:
            failures.append(f"missing_agent:{agent}")
    for tool in expected.get("required_tool_previews", []):
        if tool not in tools:
            failures.append(f"missing_tool_preview:{tool}")

    log_blob = {
        "scenario_id": scenario["id"],
        "status": actual_status,
        "block_reason": block_reason,
        "steps": [step.output for step in step_results],
    }
    for field in harness_config["forbidden_log_fields"]:
        if field in json.dumps(log_blob, ensure_ascii=False):
            failures.append(f"forbidden_log_field:{field}")

    side_effects = [
        step.output
        for step in step_results
        if step.kind == "tool_preview"
        and step.output.get("side_effect_status") not in {None, "pending"}
    ]
    if side_effects:
        failures.append("side_effect_before_approval")

    final_status = "failed" if failures else actual_status
    return {
        "scenario_id": scenario["id"],
        "description": scenario["description"],
        "status": final_status,
        "expected_status": expected["status"],
        "block_reason": block_reason,
        "agents": agents,
        "tool_previews": tools,
        "failures": failures,
        "steps": [
            {
                "type": step.kind,
                "name": step.name,
                "status": step.status,
                "output": step.output,
            }
            for step in step_results
        ],
    }


def discover_scenarios(name: str | None) -> list[Path]:
    scenario_dir = HARNESS / "scenarios"
    if name:
        path = scenario_dir / f"{name}.yaml"
        if not path.exists():
            raise HarnessError(f"Scenario not found: {name}")
        return [path]
    return sorted(scenario_dir.glob("*.yaml"))


def write_report(report: dict[str, Any]) -> Path:
    report_dir = HARNESS / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = report_dir / f"harness-run-{stamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def build_report(scenario_name: str | None) -> dict[str, Any]:
    harness_config = load_json_compatible_yaml(HARNESS / "config" / "agent_harness.yaml")
    safety_policy = load_json_compatible_yaml(HARNESS / "config" / "safety_policy.yaml")
    results = [
        run_scenario(path, harness_config, safety_policy)
        for path in discover_scenarios(scenario_name)
    ]
    return {
        "created_at": datetime.now(UTC).isoformat(),
        "harness_version": harness_config["version"],
        "summary": {
            "total": len(results),
            "passed": sum(1 for result in results if result["status"] in {"passed", "blocked"}),
            "failed": sum(1 for result in results if result["status"] == "failed"),
        },
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", help="Run one scenario by id")
    parser.add_argument("--write-report", action="store_true", help="Write JSON report under harness/reports")
    args = parser.parse_args()

    report = build_report(args.scenario)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    for result in report["results"]:
        print(f"{result['status'].upper()}: {result['scenario_id']}")
        for failure in result["failures"]:
            print(f"  - {failure}")

    if args.write_report:
        print(f"report={write_report(report)}")

    return 1 if report["summary"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

