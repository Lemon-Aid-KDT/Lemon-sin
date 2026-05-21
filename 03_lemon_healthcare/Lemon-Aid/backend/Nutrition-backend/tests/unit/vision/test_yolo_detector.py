"""YOLO ROI detector tests."""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pytest
from PIL import Image
from src.config import Settings
from src.vision.base import BoundingBox, VisionError
from src.vision.ultralytics_runner import UltralyticsYoloRunner
from src.vision.yolo import YoloLabelDetector


class _FakeRunner:
    """Fake detector runner for `YoloLabelDetector` tests."""

    def __init__(self, regions: list[BoundingBox]) -> None:
        self.regions = regions
        self.received_image_bytes: bytes | None = None

    def detect_regions(self, image_bytes: bytes) -> list[BoundingBox]:
        """Return configured regions while capturing the input.

        Args:
            image_bytes: Validated image bytes.

        Returns:
            Configured bounding boxes.
        """
        self.received_image_bytes = image_bytes
        return self.regions


class _Boxes:
    """Fake Ultralytics boxes object."""

    def __init__(self) -> None:
        self.xyxy = [[-1, 1, 9, 7], [0, 0, 5, 4], [1, 1, 4, 4]]
        self.cls = [1, 2, 0]
        self.conf = [0.86, 0.91, 0.40]


class _Result:
    """Fake Ultralytics result object."""

    def __init__(self) -> None:
        self.boxes = _Boxes()


class _FakeModel:
    """Fake Ultralytics model object."""

    def __init__(self) -> None:
        self.names: dict[int, str] = {
            0: "supplement_label",
            1: "supplement_bottle",
            2: "person",
        }

    def predict(self, *, source: Any, conf: float, verbose: bool) -> list[_Result]:
        """Return a fake result list matching the Ultralytics result shape.

        Args:
            source: PIL image passed by the runner.
            conf: Confidence threshold.
            verbose: Verbose flag.

        Returns:
            Fake result list.
        """
        assert source.size == (10, 8)
        assert conf == 0.5
        assert verbose is False
        return [_Result()]


def _settings(
    *,
    enable_vision_classifier: bool = True,
    vision_roi_allowed_classes: list[str] | None = None,
) -> Settings:
    """Return settings for detector tests.

    Args:
        enable_vision_classifier: Whether the gated YOLO channel is enabled.
        vision_roi_allowed_classes: Optional ROI taxonomy override.

    Returns:
        Settings object.
    """
    if vision_roi_allowed_classes is None:
        return Settings(enable_vision_classifier=enable_vision_classifier)
    return Settings(
        enable_vision_classifier=enable_vision_classifier,
        vision_roi_allowed_classes=vision_roi_allowed_classes,
    )


def _fake_model_factory(_name: str) -> _FakeModel:
    """Return a fake YOLO model for runner tests.

    Args:
        _name: Model name accepted for parity with the production model factory.

    Returns:
        Fake model satisfying the runner protocol.
    """
    return _FakeModel()


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


@pytest.mark.asyncio
async def test_yolo_label_detector_rejects_when_feature_flag_disabled() -> None:
    """Verify YOLO inference is fail-closed when the feature flag is false."""
    detector = YoloLabelDetector(Settings(), runner=_FakeRunner([]))

    with pytest.raises(VisionError, match="ENABLE_VISION_CLASSIFIER=false"):
        await detector.detect_label_region(_png_bytes())


@pytest.mark.asyncio
async def test_yolo_label_detector_selects_best_label_region() -> None:
    """Verify the detector returns ROI metadata rather than text facts."""
    runner = _FakeRunner(
        [
            BoundingBox(
                x=0,
                y=0,
                width=10,
                height=8,
                confidence=0.99,
                label="supplement_bottle",
            ),
            BoundingBox(
                x=2,
                y=1,
                width=4,
                height=3,
                confidence=0.55,
                label="supplement_label",
            ),
        ]
    )
    detector = YoloLabelDetector(_settings(), runner=runner)

    region = await detector.detect_label_region(_png_bytes())

    assert region.label == "supplement_label"
    assert region.model is None
    assert runner.received_image_bytes is not None


@pytest.mark.asyncio
async def test_yolo_label_detector_rejects_unknown_allowed_labels() -> None:
    """Verify an invalid ROI taxonomy cannot silently enable detection."""
    detector = YoloLabelDetector(
        _settings(vision_roi_allowed_classes=["nutrition_facts_text"]),
        runner=None,
    )

    with pytest.raises(VisionError, match="VISION_ROI_ALLOWED_CLASSES"):
        await detector.detect_label_region(_png_bytes())


def test_ultralytics_runner_normalizes_allowed_boxes_without_text_extraction() -> None:
    """Verify Ultralytics boxes become bounded ROI metadata only."""
    runner = UltralyticsYoloRunner(
        model_name="local-supplement-roi.pt",
        allowed_labels={"supplement_bottle", "supplement_label", "blister_pack"},
        min_confidence=0.5,
        model_factory=_fake_model_factory,
    )

    regions = runner.detect_regions(_png_bytes())

    assert regions == [
        BoundingBox(
            x=0,
            y=1,
            width=9,
            height=6,
            confidence=0.86,
            label="supplement_bottle",
            model="local-supplement-roi.pt",
        )
    ]


def test_ultralytics_runner_fails_closed_without_allowed_boxes() -> None:
    """Verify unknown classes are ignored and produce a stable vision error."""
    runner = UltralyticsYoloRunner(
        model_name="local-supplement-roi.pt",
        allowed_labels={"blister_pack"},
        min_confidence=0.5,
        model_factory=_fake_model_factory,
    )

    with pytest.raises(VisionError, match="allowed supplement ROI"):
        runner.detect_regions(_png_bytes())
