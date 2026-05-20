"""Probe the optional PaddleOCR local OCR runtime.

This script is intentionally separated from ``/ready``. It performs a live
PaddleOCR import, predictor initialization, and one tiny prediction only when an
operator explicitly runs it. The JSON output is redacted: it reports counts and
status flags, not raw image bytes, raw OCR text, or provider payloads.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from importlib import import_module
from io import BytesIO
from pathlib import Path
from typing import Any, Literal, cast

BACKEND_ROOT = Path(__file__).resolve().parents[1]
NUTRITION_BACKEND_ROOT = BACKEND_ROOT / "Nutrition-backend"
if str(NUTRITION_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(NUTRITION_BACKEND_ROOT))

from src.config import Settings  # noqa: E402
from src.ocr.base import OCRImageInput, OCRResult  # noqa: E402
from src.ocr.providers.paddle import PaddleOCRAdapter  # noqa: E402

LocalOCREngine = Literal["paddle", "paddle_static", "paddle_dynamic", "transformers"]
LOCAL_OCR_ENGINE_VALUES = ("paddle", "paddle_static", "paddle_dynamic", "transformers")


def main() -> None:
    """Run the explicit PaddleOCR runtime probe."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", "--image-path", dest="image", type=Path, default=None)
    parser.add_argument("--language", default="korean")
    parser.add_argument("--device", default=None)
    parser.add_argument("--engine", choices=LOCAL_OCR_ENGINE_VALUES, default="paddle")
    parser.add_argument("--paddlex-config", default=None)
    parser.add_argument("--text-recognition-model-dir", default=None)
    parser.add_argument("--text-detection-model-dir", default=None)
    parser.add_argument("--text-recognition-model-name", default=None)
    parser.add_argument("--text-detection-model-name", default=None)
    parser.add_argument("--use-doc-orientation-classify", action="store_true")
    parser.add_argument("--use-doc-unwarping", action="store_true")
    parser.add_argument("--use-textline-orientation", action="store_true")
    args = parser.parse_args()

    summary = asyncio.run(
        probe_paddleocr_runtime(
            image_path=args.image,
            language=args.language,
            device=args.device,
            engine=args.engine,
            paddlex_config=args.paddlex_config,
            text_recognition_model_dir=args.text_recognition_model_dir,
            text_detection_model_dir=args.text_detection_model_dir,
            text_recognition_model_name=args.text_recognition_model_name,
            text_detection_model_name=args.text_detection_model_name,
            use_doc_orientation_classify=args.use_doc_orientation_classify,
            use_doc_unwarping=args.use_doc_unwarping,
            use_textline_orientation=args.use_textline_orientation,
        )
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


async def probe_paddleocr_runtime(
    *,
    image_path: Path | None,
    language: str,
    device: str | None,
    engine: str | None,
    paddlex_config: str | None,
    text_recognition_model_dir: str | None,
    text_detection_model_dir: str | None,
    text_recognition_model_name: str | None,
    text_detection_model_name: str | None,
    use_doc_orientation_classify: bool,
    use_doc_unwarping: bool,
    use_textline_orientation: bool,
) -> dict[str, object]:
    """Run a redacted PaddleOCR runtime probe.

    Args:
        image_path: Optional local image path. When omitted, a generated tiny
            non-sensitive fixture image is used.
        language: PaddleOCR language setting.
        device: Optional PaddleOCR device selector.
        engine: Optional PaddleOCR 3.x inference engine.
        paddlex_config: Optional PaddleX config path.
        text_recognition_model_dir: Optional fine-tuned recognition model directory.
        text_detection_model_dir: Optional fine-tuned detection model directory.
        text_recognition_model_name: Optional recognition model name.
        text_detection_model_name: Optional detection model name.
        use_doc_orientation_classify: Whether to run document orientation classification.
        use_doc_unwarping: Whether to run document unwarping.
        use_textline_orientation: Whether to run textline orientation classification.

    Returns:
        Redacted probe summary.
    """
    try:
        import_module("paddleocr")
    except Exception as exc:
        return _failure_summary(stage="import", exc=exc)

    try:
        image = _load_image_input(image_path) if image_path is not None else _fixture_image_input()
        settings = Settings(
            _env_file=None,
            enable_local_ocr=True,
            local_ocr_language=language,
            local_ocr_device=device,
            local_ocr_engine=_parse_engine(engine),
            local_ocr_use_doc_orientation_classify=use_doc_orientation_classify,
            local_ocr_use_doc_unwarping=use_doc_unwarping,
            local_ocr_use_textline_orientation=use_textline_orientation,
            local_ocr_paddlex_config=paddlex_config,
            local_ocr_text_recognition_model_dir=text_recognition_model_dir,
            local_ocr_text_detection_model_dir=text_detection_model_dir,
            local_ocr_text_recognition_model_name=text_recognition_model_name,
            local_ocr_text_detection_model_name=text_detection_model_name,
            local_ocr_confidence_threshold=0.0,
        )
        result = await PaddleOCRAdapter(settings).extract_text(image)
    except Exception as exc:
        return _failure_summary(stage="predict", exc=exc)
    return _success_summary(result)


def _fixture_image_input() -> OCRImageInput:
    """Build a generated non-sensitive probe image.

    Returns:
        OCR input containing a tiny generated PNG.
    """
    image_module, image_draw_module, image_font_module = _pillow_modules()

    image = image_module.new("RGB", (240, 80), "white")
    drawer = image_draw_module.Draw(image)
    drawer.text(
        (12, 28),
        "Vitamin D 25 ug",
        fill="black",
        font=image_font_module.load_default(),
    )
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return OCRImageInput(
        image_bytes=buffer.getvalue(),
        mime_type="image/png",
        width=image.width,
        height=image.height,
    )


def _load_image_input(image_path: Path) -> OCRImageInput:
    """Load an operator-supplied image into the OCR input DTO.

    Args:
        image_path: Local image path.

    Returns:
        OCR image input with decoded dimensions.

    Raises:
        RuntimeError: If Pillow is unavailable or the image cannot be decoded.
    """
    image_module, _, _ = _pillow_modules()

    image_bytes = image_path.read_bytes()
    with image_module.open(BytesIO(image_bytes)) as image:
        width, height = image.size
        mime_type = image_module.MIME.get(image.format or "", "image/png")
    return OCRImageInput(
        image_bytes=image_bytes,
        mime_type=mime_type,
        width=width,
        height=height,
    )


def _pillow_modules() -> tuple[Any, Any, Any]:
    """Import Pillow modules for explicit probe image operations.

    Returns:
        Pillow Image, ImageDraw, and ImageFont modules.

    Raises:
        RuntimeError: If Pillow is unavailable.
    """
    try:
        image_module = import_module("PIL.Image")
        image_draw_module = import_module("PIL.ImageDraw")
        image_font_module = import_module("PIL.ImageFont")
    except ImportError as exc:
        raise RuntimeError("Pillow is required for the PaddleOCR runtime probe.") from exc
    return image_module, image_draw_module, image_font_module


def _parse_engine(value: str | None) -> LocalOCREngine | None:
    """Validate a PaddleOCR engine CLI value.

    Args:
        value: Candidate CLI value.

    Returns:
        Typed engine value or None.

    Raises:
        ValueError: If the value is unsupported.
    """
    if value is None:
        return None
    if value not in LOCAL_OCR_ENGINE_VALUES:
        raise ValueError(f"Unsupported LOCAL_OCR_ENGINE: {value}")
    return cast(LocalOCREngine, value)


def _success_summary(result: OCRResult) -> dict[str, object]:
    """Build a redacted success summary.

    Args:
        result: OCR result from the local PaddleOCR adapter.

    Returns:
        Redacted success summary.
    """
    return {
        "ok": True,
        "stage": "predict",
        "provider": result.provider,
        "text_present": bool(result.text.strip()),
        "text_line_count": len([line for line in result.text.splitlines() if line.strip()]),
        "confidence_present": result.confidence is not None,
        "pages_count": len(result.pages),
        "layout_available": bool(result.pages),
        "raw_image_stored": False,
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
    }


def _failure_summary(*, stage: str, exc: Exception) -> dict[str, object]:
    """Build a redacted failure summary.

    Args:
        stage: Probe stage that failed.
        exc: Exception raised by import, fixture creation, or prediction.

    Returns:
        Redacted failure summary.
    """
    return {
        "ok": False,
        "stage": stage,
        "error_type": exc.__class__.__name__,
        "message": str(exc),
        "raw_image_stored": False,
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
    }


if __name__ == "__main__":
    main()
