"""Run a local supplement analyze API smoke test with raw-leak checks.

This operator script validates the product API path used by Flutter:
``POST /api/v1/supplements/analyze`` with a multipart image upload. It prints
and optionally writes only a bounded summary. Raw OCR text, provider payloads,
request headers, model responses, image bytes, and secrets are rejected.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import httpx

ProviderSelector = Literal["configured", "paddleocr", "clova", "google_vision"]

ANALYZE_PATH = "/supplements/analyze"
DEFAULT_BASE_URL = "http://127.0.0.1:8000/api/v1"
DEFAULT_TIMEOUT_SECONDS = 120.0
EXTERNAL_PROVIDER_SELECTORS = frozenset({"clova", "google_vision"})
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "10.0.2.2"})
RAW_FORBIDDEN_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "bearer_token",
        "clova_ocr_secret",
        "google_cloud_api_key",
        "image",
        "image_base64",
        "image_bytes",
        "ocr_text",
        "provider_payload",
        "raw_image",
        "raw_model_response",
        "raw_ocr_text",
        "raw_provider_payload",
        "request_headers",
        "secret",
        "service_key",
        "x_ocr_secret",
        "x-goog-api-key",
    }
)
MAX_SAFE_MESSAGE_CHARS = 200


@dataclass(frozen=True)
class AnalyzeSmokeRequest:
    """Validated local analyze smoke request.

    Args:
        base_url: Backend API base URL ending in ``/api/v1``.
        image_path: Local supplement label image path.
        provider: OCR provider selector submitted to the API.
        client_request_id: Bounded idempotency key for this smoke request.
        bearer_token: Optional token read from an environment variable.
        timeout_seconds: HTTP timeout.
    """

    base_url: str
    image_path: Path
    provider: ProviderSelector
    client_request_id: str
    bearer_token: str | None
    timeout_seconds: float


def main() -> None:
    """Parse CLI args, run the smoke request, and print a redacted summary."""
    args = _parse_args()
    request = build_smoke_request(args)
    if args.dry_run:
        summary = {
            "dry_run": True,
            "base_url": request.base_url,
            "image_path": str(request.image_path),
            "provider": request.provider,
            "client_request_id": request.client_request_id,
            "token_configured": bool(request.bearer_token),
        }
    else:
        summary = run_smoke(request)

    if args.output_summary is not None:
        args.output_summary.parent.mkdir(parents=True, exist_ok=True)
        args.output_summary.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def build_smoke_request(args: argparse.Namespace) -> AnalyzeSmokeRequest:
    """Build a validated smoke request from CLI arguments.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Validated smoke request.

    Raises:
        SystemExit: If a local-only or external-provider guard is violated.
    """
    base_url = str(args.base_url).rstrip("/")
    image_path = args.image.expanduser().resolve()
    provider = args.provider
    if provider in EXTERNAL_PROVIDER_SELECTORS and not args.allow_external_provider:
        raise SystemExit("External OCR provider selectors require --allow-external-provider.")
    if not args.allow_non_loopback and not _is_loopback_api_url(base_url):
        raise SystemExit("Non-loopback API URLs require --allow-non-loopback.")
    if not image_path.is_file():
        raise SystemExit(f"Image path does not exist: {image_path}")
    token = _token_from_env(args.token_env)
    return AnalyzeSmokeRequest(
        base_url=base_url,
        image_path=image_path,
        provider=provider,
        client_request_id=args.client_request_id,
        bearer_token=token,
        timeout_seconds=args.timeout,
    )


def run_smoke(request: AnalyzeSmokeRequest) -> dict[str, object]:
    """Execute one supplement analyze request and return a redacted summary.

    Args:
        request: Validated smoke request.

    Returns:
        Redacted response summary.

    Raises:
        SystemExit: If the API response includes forbidden raw fields.
    """
    url = f"{request.base_url}{ANALYZE_PATH}"
    headers = {"Accept": "application/json"}
    if request.bearer_token:
        headers["Authorization"] = f"Bearer {request.bearer_token}"

    with request.image_path.open("rb") as image_file:
        files = {
            "image": (
                request.image_path.name,
                image_file,
                _guess_content_type(request.image_path),
            )
        }
        data = {
            "client_request_id": request.client_request_id,
            "ocr_provider": request.provider,
        }
        with httpx.Client(timeout=request.timeout_seconds) as client:
            response = client.post(url, headers=headers, data=data, files=files)

    payload = _decode_json_payload(response)
    assert_no_forbidden_raw_fields(payload)
    if response.status_code != httpx.codes.ACCEPTED:
        return _unexpected_status_summary(response.status_code, payload)
    return summarize_preview(payload, status_code=response.status_code)


def summarize_preview(payload: dict[str, Any], *, status_code: int) -> dict[str, object]:
    """Summarize a safe supplement preview without raw OCR text.

    Args:
        payload: API response payload already scanned for forbidden keys.
        status_code: HTTP status code.

    Returns:
        Bounded summary for logs or artifact storage.
    """
    observations = _list_of_dicts(payload.get("provider_observations"))
    return {
        "status_code": status_code,
        "api_status": payload.get("status"),
        "analysis_id_present": isinstance(payload.get("analysis_id"), str),
        "ingredient_candidate_count": len(_list_of_dicts(payload.get("ingredient_candidates"))),
        "provider_observation_count": len(observations),
        "providers": _unique_strings(observation.get("provider") for observation in observations),
        "stages": _unique_strings(observation.get("stage") for observation in observations),
        "provider_statuses": _unique_strings(
            observation.get("status") for observation in observations
        ),
        "text_non_empty_observations": sum(
            1 for observation in observations if observation.get("text_non_empty") is True
        ),
        "raw_ocr_text_stored": _any_true(
            observation.get("raw_ocr_text_stored") for observation in observations
        ),
        "raw_provider_payload_stored": _any_true(
            observation.get("raw_provider_payload_stored") for observation in observations
        ),
        "warning_count": len(_string_items(payload.get("warnings"))),
        "action_required": payload.get("action_required"),
        "image_quality_status": _image_quality_status(payload.get("image_quality_report")),
        "raw_forbidden": False,
    }


def assert_no_forbidden_raw_fields(value: object) -> None:
    """Reject response content that exposes raw OCR, payload, image, or secrets.

    Args:
        value: JSON-compatible response value.

    Raises:
        SystemExit: If a forbidden raw field name is found.
    """
    forbidden_path = _find_forbidden_raw_field(value, path="$")
    if forbidden_path is not None:
        raise SystemExit(f"Forbidden raw field in API response: {forbidden_path}")


def _parse_args() -> argparse.Namespace:
    """Return parsed command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument(
        "--provider",
        choices=("configured", "paddleocr", "clova", "google_vision"),
        default="paddleocr",
    )
    parser.add_argument("--client-request-id", default="local-api-smoke")
    parser.add_argument(
        "--token-env",
        default="LEMON_API_TOKEN",
        help="Environment variable containing the bearer token. The token is never printed.",
    )
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--output-summary", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--allow-external-provider",
        action="store_true",
        help="Required before selecting CLOVA or Google Vision.",
    )
    parser.add_argument(
        "--allow-non-loopback",
        action="store_true",
        help="Required before sending images to a non-loopback API URL.",
    )
    return parser.parse_args()


def _decode_json_payload(response: httpx.Response) -> dict[str, Any]:
    """Decode an HTTP response as a JSON object without printing the body."""
    try:
        payload = response.json()
    except ValueError as exc:
        raise SystemExit(f"API returned non-JSON response: status={response.status_code}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"API returned non-object JSON: status={response.status_code}")
    return payload


def _unexpected_status_summary(status_code: int, payload: dict[str, Any]) -> dict[str, object]:
    """Build a bounded non-success response summary."""
    detail = payload.get("detail")
    error_code = None
    message = None
    if isinstance(detail, dict):
        error_code = _safe_string(detail.get("code"))
        message = _safe_string(detail.get("message"))
    return {
        "status_code": status_code,
        "api_status": "unexpected_status",
        "error_code": error_code,
        "message": message,
        "raw_forbidden": False,
    }


def _find_forbidden_raw_field(value: object, *, path: str) -> str | None:
    """Return the first forbidden field path in a JSON-compatible value."""
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized_key = str(key).lower()
            next_path = f"{path}.{key}"
            if normalized_key in RAW_FORBIDDEN_KEYS:
                return next_path
            found = _find_forbidden_raw_field(nested, path=next_path)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found = _find_forbidden_raw_field(item, path=f"{path}[{index}]")
            if found is not None:
                return found
    return None


def _token_from_env(name: str) -> str | None:
    """Read a bearer token from the named environment variable."""
    token = os.environ.get(name, "").strip()
    return token or None


def _is_loopback_api_url(value: str) -> bool:
    """Return whether the API URL points at a local simulator/dev host."""
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and parsed.hostname in LOOPBACK_HOSTS


def _guess_content_type(path: Path) -> str:
    """Guess a safe image content type for multipart upload."""
    guessed, _encoding = mimetypes.guess_type(path.name)
    if guessed in {"image/jpeg", "image/png", "image/webp"}:
        return guessed
    return "application/octet-stream"


def _list_of_dicts(value: object) -> list[dict[str, Any]]:
    """Return dictionary items from a JSON list value."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_items(value: object) -> list[str]:
    """Return string items from a JSON list value."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _unique_strings(values: object) -> list[str]:
    """Return sorted unique strings from an iterable-like input."""
    if not hasattr(values, "__iter__"):
        return []
    return sorted({value for value in values if isinstance(value, str) and value})


def _any_true(values: object) -> bool:
    """Return whether any iterable item is explicitly true."""
    if not hasattr(values, "__iter__"):
        return False
    return any(value is True for value in values)


def _safe_string(value: object) -> str | None:
    """Return a bounded string for unexpected-status summaries."""
    if not isinstance(value, str):
        return None
    return value[:MAX_SAFE_MESSAGE_CHARS]


def _image_quality_status(value: object) -> str | None:
    """Return the bounded image-quality status from the preview."""
    if not isinstance(value, dict):
        return None
    status = value.get("status")
    return status if isinstance(status, str) else None


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
