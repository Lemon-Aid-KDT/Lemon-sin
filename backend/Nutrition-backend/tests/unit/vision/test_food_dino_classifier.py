"""FoodDinoClassifier passes the optional CLIP food-filter settings through.

The adapter lazily imports the heavy team classifier, so these tests stub the module
loader and assert the new ``enable_food_filter`` / threshold / model-id kwargs reach the
team ``FoodClassifier`` (and default to off).
"""

from __future__ import annotations

from typing import Any, ClassVar

import pytest
from src.vision import food_dino_classifier
from src.vision.food_dino_classifier import FoodDinoClassifier


class _FakeFoodClassifier:
    """Records the kwargs the adapter constructs it with."""

    last_kwargs: ClassVar[dict[str, Any]] = {}

    def __init__(self, **kwargs: Any) -> None:
        _FakeFoodClassifier.last_kwargs = dict(kwargs)

    def analyze(self, _image: Any) -> None:
        return None


class _FakeModule:
    FoodClassifier = _FakeFoodClassifier


def _adapter(**overrides: Any) -> FoodDinoClassifier:
    kwargs: dict[str, Any] = {
        "module_dir": "/unused",
        "exp16b_model_path": "/x/best.pt",
        "probe_path": "/x/probe.pt",
        "nutrition_csv_path": "/x/n.csv",
        "model_label": "food_dino_exp16b",
        "detector_confidence": 0.1,
        "max_px": 896,
    }
    kwargs.update(overrides)
    return FoodDinoClassifier(**kwargs)


def test_clip_filter_settings_are_passed_to_team_classifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        food_dino_classifier, "_load_food_classifier_module", lambda _dir: _FakeModule
    )
    adapter = _adapter(
        enable_food_filter=True,
        food_filter_threshold=0.7,
        food_filter_model_id="openai/clip-vit-large-patch14",
    )

    adapter._load_classifier()

    kwargs = _FakeFoodClassifier.last_kwargs
    assert kwargs["enable_food_filter"] is True
    assert kwargs["food_filter_threshold"] == 0.7
    assert kwargs["food_filter_model_id"] == "openai/clip-vit-large-patch14"
    # The existing classifier kwargs still flow through.
    assert kwargs["det_conf"] == 0.1
    assert kwargs["max_px"] == 896


def test_clip_filter_defaults_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        food_dino_classifier, "_load_food_classifier_module", lambda _dir: _FakeModule
    )
    adapter = _adapter()

    adapter._load_classifier()

    kwargs = _FakeFoodClassifier.last_kwargs
    assert kwargs["enable_food_filter"] is False
    assert kwargs["food_filter_threshold"] == 0.5
    assert kwargs["food_filter_model_id"] == "openai/clip-vit-base-patch16"
