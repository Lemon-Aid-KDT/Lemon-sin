"""Tests for redacted supplement OCR observation collection."""

from __future__ import annotations

import hashlib
import json
import os
from io import BytesIO
from pathlib import Path
from typing import Any, cast

import pytest
from PIL import Image
from src.ocr.base import OCRImageInput, OCRResult

from scripts import collect_supplement_ocr_observations as collect


def _write_manifest(path: Path, image_bytes: bytes) -> None:
    """Write a minimal safe OCR gate manifest.

    Args:
        path: Destination manifest path.
        image_bytes: Fixture image bytes used for checksum.
    """
    image_path = path.parent / "label.png"
    image_path.write_bytes(image_bytes)
    row = {
        "fixture_id": "fixture-001",
        "image_path": "label.png",
        "image_sha256": hashlib.sha256(image_bytes).hexdigest(),
        "license_status": "synthetic",
        "consent_status": "not_required",
        "contains_personal_data": False,
        "labels": ["synthetic"],
        "expected": {"ingredients": [{"name": "vitamin c", "amount": 500, "unit": "mg"}]},
    }
    path.write_text(json.dumps({"version": "test-v1", "cases": [row]}), encoding="utf-8")


def _png_bytes() -> bytes:
    """Return a valid tiny PNG for live-collection unit tests.

    Returns:
        PNG bytes.
    """
    image = Image.new("RGB", (120, 80), "white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class _FakeOCRAdapter:
    """Fake OCR adapter returning deterministic supplement text."""

    async def extract_text(self, _image: OCRImageInput) -> OCRResult:
        """Return OCR text containing one ingredient candidate.

        Args:
            _image: OCR input ignored by the fake.

        Returns:
            OCR result.
        """
        return OCRResult(
            text="Lemon Health Vitamin\nVitamin C 500 mg",
            provider="google_vision",
            confidence=0.9,
        )


async def test_collect_observations_defaults_to_redacted_not_run(tmp_path: Path) -> None:
    """Verify provider observations are safe when live opt-in env vars are absent."""
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, b"fixture-image")

    observations = await collect.collect_observations(
        manifest_path=manifest_path,
        providers=("google_vision_document", "paddleocr_local", "clova_ocr"),
    )

    assert len(observations) == 3
    assert {row["status"] for row in observations} == {"not_run"}
    dumped = json.dumps(observations, ensure_ascii=False)
    assert "raw_ocr_text" not in dumped
    assert "ocr_text" not in dumped
    assert "fixture-image" not in dumped
    assert all("text_hash" not in row for row in observations)


async def test_collect_observations_rejects_raw_manifest_text(tmp_path: Path) -> None:
    """Verify raw OCR text cannot enter collector manifests."""
    manifest_path = tmp_path / "manifest.jsonl"
    manifest_path.write_text(
        json.dumps(
            {
                "fixture_id": "bad",
                "image_path": "label.png",
                "contains_personal_data": False,
                "raw_ocr_text": "secret",
            }
        ),
        encoding="utf-8",
    )

    try:
        await collect.collect_observations(
            manifest_path=manifest_path,
            providers=("google_vision_document",),
        )
    except ValueError as exc:
        assert "raw_ocr_text" in str(exc)
    else:
        raise AssertionError("Expected raw OCR text rejection.")


async def test_collect_observations_can_seed_google_auto_expected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Google Vision auto expected snapshots are provisional and redacted."""
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, _png_bytes())
    seeded_manifest_path = tmp_path / "seeded" / "manifest.json"
    monkeypatch.setenv("RUN_GOOGLE_VISION_SMOKE", "1")
    monkeypatch.setattr(
        collect,
        "_build_provider_adapter",
        lambda _provider, _settings: _FakeOCRAdapter(),
    )

    collection = await collect.collect_observations_with_auto_expected(
        manifest_path=manifest_path,
        providers=("google_vision_document",),
        auto_expected_provider="google_vision_document",
        auto_expected_manifest_path=seeded_manifest_path,
    )

    assert len(collection.observations) == 1
    observation = collection.observations[0]
    assert observation["status"] == "completed"
    assert observation["text_non_empty"] is True
    auto_manifest = cast(dict[str, Any] | None, collection.auto_expected_manifest)
    assert auto_manifest is not None
    expected = auto_manifest["cases"][0]["expected"]
    assert expected["expected_source"] == "google_vision_auto_seed"
    assert expected["verification_status"] == "provisional"
    assert expected["seed_provider"] == "google_vision_document"
    assert expected["ingredients"] == [
        {
            "name": "Vitamin C",
            "amount": 500,
            "unit": "mg",
            "expected_source": "google_vision_auto_seed",
            "verification_status": "provisional",
        }
    ]
    dumped = json.dumps(auto_manifest, ensure_ascii=False)
    assert "raw_ocr_text" not in dumped
    assert "provider_payload" not in dumped
    assert "Lemon Health Vitamin\nVitamin C 500 mg" not in dumped


async def test_collect_observations_loads_allowlisted_operator_env_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify collector can opt in to live providers from a redacted dotenv file."""
    manifest_path = tmp_path / "manifest.json"
    env_path = tmp_path / ".env"
    _write_manifest(manifest_path, _png_bytes())
    env_path.write_text(
        "\n".join(
            [
                "RUN_GOOGLE_VISION_SMOKE=1",
                "OCR_PRIMARY_PROVIDER=google_vision",
                "ALLOW_EXTERNAL_OCR=true",
                "GOOGLE_VISION_AUTH_MODE=api_key",
                "GOOGLE_CLOUD_API_KEY=test-secret-key",
                "UNRELATED_SECRET=must-not-load",
            ]
        ),
        encoding="utf-8",
    )
    for key in (
        "RUN_GOOGLE_VISION_SMOKE",
        "OCR_PRIMARY_PROVIDER",
        "ALLOW_EXTERNAL_OCR",
        "GOOGLE_VISION_AUTH_MODE",
        "GOOGLE_CLOUD_API_KEY",
        "UNRELATED_SECRET",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(
        collect,
        "_build_provider_adapter",
        lambda _provider, _settings: _FakeOCRAdapter(),
    )

    collection = await collect.collect_observations_with_auto_expected(
        manifest_path=manifest_path,
        providers=("google_vision_document",),
        auto_expected_provider="google_vision_document",
        auto_expected_manifest_path=tmp_path / "seeded" / "manifest.json",
        env_file=env_path,
    )

    assert collection.observations[0]["status"] == "completed"
    assert "UNRELATED_SECRET" not in os.environ
    assert "GOOGLE_CLOUD_API_KEY" not in os.environ
    dumped = json.dumps(
        {
            "observations": collection.observations,
            "auto_expected_manifest": collection.auto_expected_manifest,
        },
        ensure_ascii=False,
    )
    assert "test-secret-key" not in dumped
    assert "GOOGLE_CLOUD_API_KEY" not in dumped


def test_operator_env_file_does_not_override_existing_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify shell-provided opt-in values take precedence over dotenv."""
    env_path = tmp_path / ".env"
    env_path.write_text("RUN_GOOGLE_VISION_SMOKE=1\n", encoding="utf-8")
    monkeypatch.setenv("RUN_GOOGLE_VISION_SMOKE", "0")

    loaded = collect._load_operator_env_file(env_path)

    assert loaded == {}
    assert os.environ["RUN_GOOGLE_VISION_SMOKE"] == "0"
