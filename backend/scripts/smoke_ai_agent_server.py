"""Run a live FastAPI + PostgreSQL + SGLang AI Agent smoke test."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
NUTRITION_BACKEND_ROOT = BACKEND_ROOT / "Nutrition-backend"
AI_AGENT_SRC = BACKEND_ROOT / "ai_agent_chat" / "src"
DEFAULT_SERVER_URL = "http://127.0.0.1:18080"
DEFAULT_SGLANG_BASE_URL = "http://127.0.0.1:30000/v1"
DEFAULT_SGLANG_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"


def main() -> int:
    args = _parse_args()

    if not args.database_url:
        print("ERROR: set TEST_DATABASE_URL or pass --database-url.", file=sys.stderr)
        return 2

    sglang_check = "skipped" if args.skip_sglang_check else "required"
    if not args.skip_sglang_check:
        _require_sglang(args.sglang_base_url, args.timeout)

    env = _server_env(args.database_url, args.sglang_base_url, args.sglang_model)
    if not args.skip_db_upgrade:
        _run([sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"], env=env)

    process = None if args.use_existing_server else _start_server(args.server_url, env)
    try:
        _wait_for_health(args.server_url, args.timeout)
        consent = _post_json(
            f"{args.server_url}/api/v1/me/privacy/consents/sensitive_health_analysis",
            {},
            timeout=args.timeout,
        )
        first = _post_json(
            f"{args.server_url}/api/v1/ai-agent/daily-coaching",
            _daily_coaching_payload("server-smoke-1"),
            timeout=args.timeout,
        )
        second = _post_json(
            f"{args.server_url}/api/v1/ai-agent/daily-coaching",
            _daily_coaching_payload("server-smoke-2"),
            timeout=args.timeout,
        )
    finally:
        if process is not None:
            _stop_server(process)

    _assert_response(consent.get("granted") is True, "consent grant failed")
    _assert_response(first.get("status") == "completed", "first coaching request did not complete")
    _assert_response(second.get("status") == "completed", "second coaching request did not complete")
    _assert_response(
        "agent_memory" in second.get("used_tools", []),
        "second coaching request did not reload persisted agent_memory",
    )
    _assert_response(
        second.get("provider") in {"sglang", "deterministic"},
        "unexpected provider in coaching response",
    )

    print(
        json.dumps(
            _summary_payload(
                args=args,
                sglang_check=sglang_check,
                first=first,
                second=second,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-url", default=DEFAULT_SERVER_URL)
    parser.add_argument(
        "--sglang-base-url",
        default=os.getenv("SGLANG_BASE_URL", DEFAULT_SGLANG_BASE_URL),
    )
    parser.add_argument("--sglang-model", default=os.getenv("SGLANG_MODEL", DEFAULT_SGLANG_MODEL))
    parser.add_argument("--database-url", default=os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL"))
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--skip-db-upgrade", action="store_true")
    parser.add_argument(
        "--skip-sglang-check",
        action="store_true",
        help="Skip /v1/models readiness and allow deterministic fallback smoke.",
    )
    parser.add_argument(
        "--use-existing-server",
        action="store_true",
        help="Call an already running FastAPI server instead of starting uvicorn.",
    )
    return parser.parse_args(argv)


def _summary_payload(
    *,
    args: argparse.Namespace,
    sglang_check: str,
    first: dict[str, Any],
    second: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "ok",
        "server_url": args.server_url,
        "sglang_base_url": args.sglang_base_url,
        "sglang_check": sglang_check,
        "model": args.sglang_model,
        "first_provider": first.get("provider"),
        "second_provider": second.get("provider"),
        "second_used_tools": second.get("used_tools", []),
    }


def _server_env(database_url: str, sglang_base_url: str, sglang_model: str) -> dict[str, str]:
    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH")
    paths = [str(NUTRITION_BACKEND_ROOT), str(AI_AGENT_SRC), str(BACKEND_ROOT)]
    if existing_pythonpath:
        paths.append(existing_pythonpath)
    env.update(
        {
            "PYTHONPATH": os.pathsep.join(paths),
            "DATABASE_URL": database_url,
            "AUTH_MODE": "disabled",
            "LLM_PROVIDER": "sglang",
            "SGLANG_BASE_URL": sglang_base_url,
            "SGLANG_MODEL": sglang_model,
            "SGLANG_API_KEY": os.getenv("SGLANG_API_KEY", "EMPTY"),
            "ALLOW_EXTERNAL_LLM": "false",
            "LOG_LEVEL": "WARNING",
        }
    )
    return env


def _start_server(server_url: str, env: dict[str, str]) -> subprocess.Popen[str]:
    host, port = _host_port(server_url)
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.main:app",
        "--host",
        host,
        "--port",
        str(port),
        "--log-level",
        "warning",
    ]
    return subprocess.Popen(
        command,
        cwd=NUTRITION_BACKEND_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _stop_server(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def _wait_for_health(server_url: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = _get_json(f"{server_url}/health", timeout=2)
            if response.get("status") == "ok":
                return
        except Exception as exc:
            last_error = exc
            time.sleep(0.5)
    raise RuntimeError(f"server did not become healthy: {last_error}")


def _require_sglang(base_url: str, timeout: float) -> None:
    models = _get_json(f"{base_url.rstrip('/')}/models", timeout=timeout)
    data = models.get("data")
    if not isinstance(data, list) or not data:
        raise RuntimeError("SGLang /v1/models did not return any models")


def _get_json(url: str, *, timeout: float) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json(url: str, payload: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"POST {url} failed with {exc.code}: {detail}") from exc


def _run(command: list[str], *, env: dict[str, str]) -> None:
    subprocess.run(command, cwd=BACKEND_ROOT, env=env, check=True)


def _host_port(server_url: str) -> tuple[str, int]:
    parsed = urllib.parse.urlparse(server_url)
    if parsed.hostname is None or parsed.port is None:
        raise ValueError("--server-url must include host and port")
    return parsed.hostname, parsed.port


def _assert_response(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _daily_coaching_payload(request_id: str) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "user_id": "client-supplied-user",
        "context": {
            "profile": {
                "age": 52,
                "gender": "male",
                "goals": ["meal_management"],
                "chronic_conditions": ["hypertension"],
                "medications": ["blood_pressure_medication"],
            }
        },
        "payload": {
            "date": "2026-05-20",
            "sources": [
                {
                    "source_type": "food_ocr",
                    "image_id": f"{request_id}-image",
                    "raw_ocr_text": "instant noodles sodium 2600mg",
                    "user_confirmed": True,
                }
            ],
            "foods": [
                {
                    "name": "instant noodles",
                    "meal_type": "lunch",
                    "serving_label": "1 bowl",
                    "nutrients": [
                        {"name": "sodium", "amount": 2600, "unit": "mg"},
                        {"name": "protein", "amount": 25, "unit": "g"},
                    ],
                }
            ],
            "supplements": [],
            "health_trends": [
                {
                    "metric": "meal_score",
                    "direction": "down",
                    "severity": "watch",
                    "summary": "Meal score has dropped for 7 days.",
                }
            ],
        },
    }


if __name__ == "__main__":
    raise SystemExit(main())
