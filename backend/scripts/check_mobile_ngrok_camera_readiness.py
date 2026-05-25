"""Check local readiness for mobile ngrok camera smoke testing.

The script prints sanitized status flags only. It does not print bearer tokens,
gateway tokens, raw OCR payloads, image bytes, or public ngrok URLs.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from http import HTTPStatus
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

DEV_GATEWAY_TOKEN_HEADER = "X-Lemon-Dev-Gateway-Token"


@dataclass(frozen=True)
class DeviceSummary:
    """Summarized Flutter device visibility.

    Args:
        ios_simulators: Number of visible iOS simulator devices.
        ios_physical: Number of visible physical iOS devices.
        android_emulators: Number of visible Android emulator devices.
        android_physical: Number of visible physical Android devices.
    """

    ios_simulators: int
    ios_physical: int
    android_emulators: int
    android_physical: int


@dataclass(frozen=True)
class NgrokSummary:
    """Summarized local ngrok tunnel state.

    Args:
        https_tunnels: Number of visible HTTPS tunnels.
        gateway_matches: Number of HTTPS tunnels that point to the expected gateway.
    """

    https_tunnels: int
    gateway_matches: int


@dataclass(frozen=True)
class ReadinessResult:
    """Computed readiness result.

    Args:
        exit_code: Process exit code for the selected requirements.
        status: Human-readable status label.
        details: Sanitized key/value details.
    """

    exit_code: int
    status: str
    details: dict[str, str | int | bool]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Parsed namespace.
    """
    parser = argparse.ArgumentParser(
        description="Check mobile ngrok camera smoke readiness without printing secrets.",
    )
    parser.add_argument("--backend-health-url", default="http://127.0.0.1:8000/health")
    parser.add_argument("--gateway-health-url", default="http://127.0.0.1:8010/health")
    parser.add_argument("--expected-gateway-url", default="http://127.0.0.1:8010")
    parser.add_argument("--ngrok-api-url", default="http://127.0.0.1:4041/api/tunnels")
    parser.add_argument("--flutter-bin", default="flutter")
    parser.add_argument("--timeout-seconds", type=float, default=3.0)
    parser.add_argument("--require-physical-device", action="store_true")
    parser.add_argument("--require-gateway", action="store_true")
    parser.add_argument("--require-ngrok", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run readiness checks and print a sanitized one-line summary.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    args = parse_args(argv)
    token = os.environ.get("LEMON_DEV_GATEWAY_TOKEN", "").strip()
    backend_status = fetch_http_status(args.backend_health_url, timeout=args.timeout_seconds)
    gateway_status = fetch_http_status(
        args.gateway_health_url,
        timeout=args.timeout_seconds,
        gateway_token=token or None,
    )
    devices = load_flutter_devices(args.flutter_bin)
    ngrok = load_ngrok_summary(
        args.ngrok_api_url,
        expected_gateway_url=args.expected_gateway_url,
        timeout=args.timeout_seconds,
    )
    result = evaluate_readiness(
        backend_status=backend_status,
        gateway_status=gateway_status,
        devices=devices,
        ngrok=ngrok,
        require_physical_device=args.require_physical_device,
        require_gateway=args.require_gateway,
        require_ngrok=args.require_ngrok,
    )
    print(format_result(result))
    return result.exit_code


def fetch_http_status(
    url: str,
    *,
    timeout: float,
    gateway_token: str | None = None,
) -> int | None:
    """Fetch only an HTTP status code from a URL.

    Args:
        url: URL to request.
        timeout: Request timeout in seconds.
        gateway_token: Optional gateway token header value.

    Returns:
        HTTP status code, or ``None`` when the URL is unreachable.
    """
    headers = {}
    if gateway_token:
        headers[DEV_GATEWAY_TOKEN_HEADER] = gateway_token
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            return int(response.status)
    except HTTPError as error:
        return int(error.code)
    except (OSError, URLError, ValueError):
        return None


def load_flutter_devices(flutter_bin: str) -> DeviceSummary:
    """Load Flutter device visibility using `flutter devices --machine`.

    Args:
        flutter_bin: Flutter executable path or command name.

    Returns:
        Summarized device counts. Command failures return an empty summary.
    """
    try:
        completed = subprocess.run(
            [flutter_bin, "devices", "--machine"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return DeviceSummary(
            ios_simulators=0,
            ios_physical=0,
            android_emulators=0,
            android_physical=0,
        )
    if completed.returncode != 0:
        return DeviceSummary(
            ios_simulators=0,
            ios_physical=0,
            android_emulators=0,
            android_physical=0,
        )
    return parse_flutter_devices(completed.stdout)


def parse_flutter_devices(payload: str) -> DeviceSummary:
    """Parse `flutter devices --machine` output.

    Args:
        payload: JSON device list emitted by Flutter.

    Returns:
        Summarized device counts.
    """
    try:
        devices = json.loads(payload)
    except json.JSONDecodeError:
        devices = []
    ios_simulators = 0
    ios_physical = 0
    android_emulators = 0
    android_physical = 0
    for device in devices if isinstance(devices, list) else []:
        if not isinstance(device, dict):
            continue
        platform = str(device.get("targetPlatform", "")).lower()
        is_emulator = bool(device.get("emulator"))
        if platform == "ios" and is_emulator:
            ios_simulators += 1
        elif platform == "ios":
            ios_physical += 1
        elif platform == "android" and is_emulator:
            android_emulators += 1
        elif platform == "android":
            android_physical += 1
    return DeviceSummary(
        ios_simulators=ios_simulators,
        ios_physical=ios_physical,
        android_emulators=android_emulators,
        android_physical=android_physical,
    )


def load_ngrok_summary(
    ngrok_api_url: str,
    *,
    expected_gateway_url: str,
    timeout: float,
) -> NgrokSummary:
    """Load sanitized ngrok tunnel state from the local ngrok API.

    Args:
        ngrok_api_url: Local ngrok API URL.
        expected_gateway_url: Expected local gateway upstream URL.
        timeout: Request timeout in seconds.

    Returns:
        Summarized tunnel state. Unreachable API returns an empty summary.
    """
    try:
        with urlopen(ngrok_api_url, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except (OSError, URLError, ValueError):
        return NgrokSummary(https_tunnels=0, gateway_matches=0)
    return parse_ngrok_tunnels(payload, expected_gateway_url=expected_gateway_url)


def parse_ngrok_tunnels(payload: str, *, expected_gateway_url: str) -> NgrokSummary:
    """Parse local ngrok tunnel API output without exposing public URLs.

    Args:
        payload: JSON payload from the ngrok local API.
        expected_gateway_url: Expected local gateway upstream URL.

    Returns:
        Sanitized tunnel summary.
    """
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        parsed = {}
    tunnels = parsed.get("tunnels", []) if isinstance(parsed, dict) else []
    https_tunnels = 0
    gateway_matches = 0
    for tunnel in tunnels if isinstance(tunnels, list) else []:
        if not isinstance(tunnel, dict):
            continue
        if tunnel.get("proto") != "https":
            continue
        https_tunnels += 1
        config = tunnel.get("config", {})
        addr = config.get("addr") if isinstance(config, dict) else None
        if isinstance(addr, str) and _same_loopback_endpoint(
            addr,
            expected_gateway_url,
        ):
            gateway_matches += 1
    return NgrokSummary(https_tunnels=https_tunnels, gateway_matches=gateway_matches)


def evaluate_readiness(
    *,
    backend_status: int | None,
    gateway_status: int | None,
    devices: DeviceSummary,
    ngrok: NgrokSummary,
    require_physical_device: bool,
    require_gateway: bool,
    require_ngrok: bool,
) -> ReadinessResult:
    """Evaluate selected mobile ngrok readiness requirements.

    Args:
        backend_status: Local backend health status.
        gateway_status: Local gateway health status.
        devices: Flutter device visibility summary.
        ngrok: Local ngrok tunnel summary.
        require_physical_device: Whether at least one physical mobile device is required.
        require_gateway: Whether gateway health must be HTTP 200.
        require_ngrok: Whether a matching HTTPS ngrok tunnel is required.

    Returns:
        Readiness result with sanitized details.
    """
    physical_count = devices.ios_physical + devices.android_physical
    failures = []
    if backend_status != HTTPStatus.OK:
        failures.append("backend")
    if require_gateway and gateway_status != HTTPStatus.OK:
        failures.append("gateway")
    if require_ngrok and ngrok.gateway_matches < 1:
        failures.append("ngrok")
    if require_physical_device and physical_count < 1:
        failures.append("physical_device")

    details: dict[str, str | int | bool] = {
        "backend_health": backend_status or "unreachable",
        "gateway_health": gateway_status or "unreachable",
        "ios_simulators": devices.ios_simulators,
        "ios_physical": devices.ios_physical,
        "android_emulators": devices.android_emulators,
        "android_physical": devices.android_physical,
        "ngrok_https_tunnels": ngrok.https_tunnels,
        "ngrok_gateway_matches": ngrok.gateway_matches,
        "physical_device_ready": physical_count > 0,
        "ngrok_ready": ngrok.gateway_matches > 0,
    }
    if failures:
        return ReadinessResult(exit_code=1, status="failed", details=details)
    if physical_count < 1 or ngrok.gateway_matches < 1 or gateway_status != HTTPStatus.OK:
        return ReadinessResult(exit_code=0, status="incomplete", details=details)
    return ReadinessResult(exit_code=0, status="ready", details=details)


def format_result(result: ReadinessResult) -> str:
    """Format a readiness result as a sanitized single line.

    Args:
        result: Readiness result.

    Returns:
        Single-line status string.
    """
    parts = [f"status={result.status}"]
    for key, value in result.details.items():
        parts.append(f"{key}={value}")
    return " ".join(parts)


def _same_loopback_endpoint(left: str, right: str) -> bool:
    """Compare loopback URLs while treating common loopback hostnames equally."""
    left_parts = urlsplit(left)
    right_parts = urlsplit(right)
    return (
        _normalize_loopback_host(left_parts.hostname)
        == _normalize_loopback_host(right_parts.hostname)
        and left_parts.port == right_parts.port
        and left_parts.scheme == right_parts.scheme
    )


def _normalize_loopback_host(host: str | None) -> str | None:
    """Normalize common loopback aliases for local gateway matching."""
    if host in {"localhost", "127.0.0.1", "::1"}:
        return "loopback"
    return host


if __name__ == "__main__":
    sys.exit(main())
