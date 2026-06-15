"""Food YOLO runner tests."""

from __future__ import annotations

from io import BytesIO
from typing import Any, ClassVar

import pytest
from PIL import Image
from src.vision.base import BoundingBox, VisionError
from src.vision.food_yolo import (
    FoodDetection,
    FoodYoloDetector,
    food_classifier_model_label,
    food_model_label,
)
from src.vision.taxonomy import normalize_food_vision_label, normalize_food_vision_label_set


class _Boxes:
    """Fake Ultralytics boxes object."""

    def __init__(self) -> None:
        """Create fake food detector boxes."""
        self.xyxy = [[-2, 1, 9, 7], [1, 1, 3, 3], [0, 0, 1, 1]]
        self.cls = [0, 1, 2]
        self.conf = [0.86, 0.40, 0.93]


class _Result:
    """Fake Ultralytics result object."""

    def __init__(self) -> None:
        """Create a result with boxes and names."""
        self.boxes = _Boxes()
        self.names = {0: "bibimbap", 1: "salad", 2: "rice_bowl"}


class _SingleDetectorBoxes:
    """Fake detector boxes object with one food-region candidate."""

    xyxy: ClassVar[list[list[int]]] = [[0, 0, 8, 6]]
    cls: ClassVar[list[int]] = [0]
    conf: ClassVar[list[float]] = [0.91]


class _SingleDetectorResult:
    """Fake detector result with one box."""

    def __init__(self) -> None:
        """Create a single detector result."""
        self.boxes = _SingleDetectorBoxes()
        self.names = {0: "food_item"}


class _ClassifierBoxes:
    """Fake crop classifier boxes object."""

    xyxy: ClassVar[list[list[int]]] = [[0, 0, 8, 6]]
    cls: ClassVar[list[int]] = [3]
    conf: ClassVar[list[float]] = [0.77]


class _ClassifierResult:
    """Fake crop classifier result object."""

    def __init__(self) -> None:
        """Create a crop classifier result."""
        self.boxes = _ClassifierBoxes()
        self.names = {3: "fried-chicken", 4: "rice-bowl"}


class _EmptyResult:
    """Fake empty Ultralytics result object."""

    boxes = None


class _FakeModel:
    """Fake Ultralytics model object."""

    names: ClassVar[dict[int, str]] = {0: "fallback_bibimbap"}

    def __init__(self, prediction_results: Any) -> None:
        """Initialize fake model output.

        Args:
            prediction_results: Value returned from ``predict``.
        """
        self.prediction_results = prediction_results

    def predict(self, **kwargs: Any) -> Any:
        """Return configured fake prediction results.

        Args:
            **kwargs: Keyword arguments passed by the detector.

        Returns:
            Configured prediction results.
        """
        source = kwargs["source"]
        assert source.size == (10, 8)
        assert kwargs["conf"] == 0.5
        assert kwargs["verbose"] is False
        assert kwargs["max_det"] == 5
        return self.prediction_results


class _FakeClassifierModel:
    """Fake crop classifier model."""

    names: ClassVar[dict[int, str]] = {3: "fried-chicken", 4: "rice-bowl"}

    def predict(self, **kwargs: Any) -> Any:
        """Return a configured food class prediction.

        Args:
            **kwargs: Keyword arguments passed by the detector.

        Returns:
            Fake classifier prediction results.
        """
        assert kwargs["source"].size == (8, 6)
        assert kwargs["conf"] == 0.1
        assert kwargs["verbose"] is False
        assert kwargs["classes"] == [3]
        return [_ClassifierResult()]


def _png_bytes(width: int = 10, height: int = 8) -> bytes:
    """Return a PNG fixture.

    Args:
        width: Image width.
        height: Image height.

    Returns:
        Encoded PNG bytes.
    """
    buffer = BytesIO()
    Image.new("RGB", (width, height), color=(255, 255, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_food_yolo_detector_normalizes_review_candidates() -> None:
    """Verify food YOLO emits bounded review-only candidates."""
    detector = FoodYoloDetector(
        model_path="/app/runs/food_yolo/example/weights/best.pt",
        model_label="food_yolo_local:best.pt",
        min_confidence=0.5,
        max_detections=5,
        model_factory=lambda _path: _FakeModel([_Result()]),
    )

    detections = detector.detect_foods(_png_bytes())

    assert detections == [
        FoodDetection(
            label="rice bowl",
            confidence=0.93,
            bbox=BoundingBox(
                x=0,
                y=0,
                width=1,
                height=1,
                confidence=0.93,
                label="rice bowl",
                model="food_yolo_local:best.pt",
            ),
            model="food_yolo_local:best.pt",
        ),
        FoodDetection(
            label="bibimbap",
            confidence=0.86,
            bbox=BoundingBox(
                x=0,
                y=1,
                width=9,
                height=6,
                confidence=0.86,
                label="bibimbap",
                model="food_yolo_local:best.pt",
            ),
            model="food_yolo_local:best.pt",
        ),
    ]


def test_food_yolo_detector_forwards_predict_args_and_classifier_labels() -> None:
    """Verify detector crops can be classified into nutrition class_en labels."""
    detector = FoodYoloDetector(
        model_path="/app/runs/food_yolo/detector/weights/best.pt",
        model_label="food_yolo_local:best.pt",
        min_confidence=0.5,
        max_detections=5,
        iou_threshold=0.15,
        agnostic_nms=True,
        image_size=512,
        classifier_model_path="/app/runs/food_yolo/exp16b/weights/best.pt",
        classifier_model_label="food_exp16b_local:best.pt",
        classifier_min_confidence=0.1,
        model_factory=lambda _path: _FakeModel([_SingleDetectorResult()]),
        classifier_model_factory=lambda _path: _FakeClassifierModel(),
    )

    detections = detector.detect_foods(_png_bytes())

    assert detections == [
        FoodDetection(
            label="fried-chicken",
            confidence=0.77,
            bbox=BoundingBox(
                x=0,
                y=0,
                width=8,
                height=6,
                confidence=0.77,
                label="fried-chicken",
                model="food_yolo_local:best.pt+food_exp16b_local:best.pt",
            ),
            model="food_yolo_local:best.pt+food_exp16b_local:best.pt",
            classifier_model="food_exp16b_local:best.pt",
        )
    ]


def test_food_yolo_detector_returns_empty_when_no_food_boxes() -> None:
    """Verify empty detector output degrades to manual-entry candidates."""
    detector = FoodYoloDetector(
        model_path="/app/runs/food_yolo/example/weights/best.pt",
        model_label="food_yolo_local:best.pt",
        min_confidence=0.5,
        max_detections=5,
        model_factory=lambda _path: _FakeModel([_EmptyResult()]),
    )

    assert detector.detect_foods(_png_bytes()) == []


def test_food_yolo_detector_wraps_model_load_errors() -> None:
    """Verify model load failures expose only a stable vision error."""

    def _failing_factory(_path: str) -> _FakeModel:
        raise RuntimeError("local path missing")

    detector = FoodYoloDetector(
        model_path="/app/runs/food_yolo/example/weights/best.pt",
        model_label="food_yolo_local:best.pt",
        min_confidence=0.5,
        max_detections=5,
        model_factory=_failing_factory,
    )

    with pytest.raises(VisionError, match="Food YOLO model could not be loaded"):
        detector.detect_foods(_png_bytes())


def test_food_model_label_uses_basename_only() -> None:
    """Verify model metadata does not expose local directory paths."""
    assert (
        food_model_label(
            "/app/runs/food_yolo/private/weights/best.pt",
            "food_yolo_local",
        )
        == "food_yolo_local:best.pt"
    )
    assert food_model_label(None, "food_yolo_local") is None
    assert (
        food_classifier_model_label(
            "/app/runs/food_yolo/private/exp16b/weights/best.pt",
            "food_exp16b_local",
        )
        == "food_exp16b_local:best.pt"
    )
    assert food_classifier_model_label(None, "food_exp16b_local") is None


def test_food_vision_taxonomy_normalizes_region_role_aliases() -> None:
    """Verify meal-image YOLO role labels are stable and non-medical."""
    assert normalize_food_vision_label("meal area") == "meal_region"
    assert normalize_food_vision_label("Food Object") == "food_item"
    assert normalize_food_vision_label("menu-text-region") == "menu_text"
    assert normalize_food_vision_label("Nutrition Facts Panel") == "nutrition_label"
    assert normalize_food_vision_label("diagnosis") is None
    assert normalize_food_vision_label_set(
        ["plate", "food_item", "menu", "nutrition_information", "unknown"]
    ) == ["food_item", "meal_region", "menu_text", "nutrition_label"]
