"""Tests for the mobile ngrok camera readiness preflight."""

from __future__ import annotations

import importlib
import json
import sys
from http import HTTPStatus
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[4]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

readiness = importlib.import_module("scripts.check_mobile_ngrok_camera_readiness")


def test_parse_flutter_devices_counts_simulators_and_physical_devices() -> None:
    """Verify Flutter machine output is reduced to mobile device counts."""
    payload = json.dumps(
        [
            {
                "name": "iPhone 17",
                "targetPlatform": "ios",
                "emulator": True,
            },
            {
                "name": "iPhone",
                "targetPlatform": "ios",
                "emulator": False,
            },
            {
                "name": "Pixel",
                "targetPlatform": "android",
                "emulator": False,
            },
            {
                "name": "Android SDK",
                "targetPlatform": "android",
                "emulator": True,
            },
            {
                "name": "Chrome",
                "targetPlatform": "web-javascript",
                "emulator": False,
            },
        ]
    )

    summary = readiness.parse_flutter_devices(payload)

    assert summary == readiness.DeviceSummary(
        ios_simulators=1,
        ios_physical=1,
        android_emulators=1,
        android_physical=1,
    )


def test_parse_ngrok_tunnels_counts_only_matching_https_gateway() -> None:
    """Verify ngrok parsing avoids printing URLs and matches loopback gateway."""
    payload = json.dumps(
        {
            "tunnels": [
                {
                    "proto": "https",
                    "public_url": "https://example.ngrok.app",
                    "config": {"addr": "http://localhost:8010"},
                },
                {
                    "proto": "https",
                    "public_url": "https://other.ngrok.app",
                    "config": {"addr": "http://localhost:8765"},
                },
                {
                    "proto": "http",
                    "public_url": "http://example.ngrok.app",
                    "config": {"addr": "http://127.0.0.1:8010"},
                },
            ]
        }
    )

    summary = readiness.parse_ngrok_tunnels(
        payload,
        expected_gateway_url="http://127.0.0.1:8010",
    )

    assert summary == readiness.NgrokSummary(https_tunnels=2, gateway_matches=1)


def test_evaluate_readiness_reports_incomplete_when_optional_live_gates_missing() -> None:
    """Verify missing physical device and ngrok are incomplete unless required."""
    result = readiness.evaluate_readiness(
        backend_status=HTTPStatus.OK,
        gateway_status=HTTPStatus.OK,
        devices=readiness.DeviceSummary(
            ios_simulators=1,
            ios_physical=0,
            android_emulators=0,
            android_physical=0,
        ),
        ngrok=readiness.NgrokSummary(https_tunnels=0, gateway_matches=0),
        require_physical_device=False,
        require_gateway=False,
        require_ngrok=False,
    )

    assert result.exit_code == 0
    assert result.status == "incomplete"
    assert result.details["physical_device_ready"] is False
    assert result.details["ngrok_ready"] is False


def test_evaluate_readiness_fails_when_required_live_gates_missing() -> None:
    """Verify required physical device and ngrok gates fail closed."""
    result = readiness.evaluate_readiness(
        backend_status=HTTPStatus.OK,
        gateway_status=HTTPStatus.UNAUTHORIZED,
        devices=readiness.DeviceSummary(
            ios_simulators=1,
            ios_physical=0,
            android_emulators=0,
            android_physical=0,
        ),
        ngrok=readiness.NgrokSummary(https_tunnels=1, gateway_matches=0),
        require_physical_device=True,
        require_gateway=True,
        require_ngrok=True,
    )

    assert result.exit_code == 1
    assert result.status == "failed"
    assert result.details["gateway_health"] == HTTPStatus.UNAUTHORIZED


def test_format_result_is_single_line_and_sanitized() -> None:
    """Verify result formatting contains only sanitized key/value fields."""
    result = readiness.ReadinessResult(
        exit_code=0,
        status="ready",
        details={
            "backend_health": 200,
            "gateway_health": 200,
            "ngrok_gateway_matches": 1,
            "physical_device_ready": True,
        },
    )

    formatted = readiness.format_result(result)

    assert formatted == (
        "status=ready backend_health=200 gateway_health=200 "
        "ngrok_gateway_matches=1 physical_device_ready=True"
    )
    assert "ngrok.app" not in formatted
    assert "token" not in formatted.lower()
