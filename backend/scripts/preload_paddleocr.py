"""Pre-warm the PaddleOCR Korean model cache during Docker image build.

The first PaddleOCR call downloads the configured model bundle from an
external host. In closed-network production environments, that fetch
either hangs or fails. We side-step the problem by instantiating the
predictor inside the image build so the model is already cached at
``~/.paddleocr`` (or the equivalent PaddleX cache root).

The script tolerates missing optional dependencies — if ``paddleocr`` is
not installed (for example, when an operator builds a slim image without
the ``[ocr-local]`` extras), it exits cleanly with a log message instead
of failing the image build.
"""

from __future__ import annotations

import os
import sys

_DEFAULT_LANGUAGE = "korean"


def main() -> int:
    """Instantiate a PaddleOCR predictor to warm the model cache.

    Returns:
        Process exit code. ``0`` on success and on graceful skips.
    """
    # Match the runtime default so the cache load itself does not hit a hoster.
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "true")

    try:
        from paddleocr import PaddleOCR  # type: ignore[import-not-found]  # noqa: PLC0415
    except ImportError:
        sys.stdout.write(
            "preload_paddleocr: paddleocr extras not installed; skipping cache warm-up.\n"
        )
        return 0

    language = os.environ.get("LOCAL_OCR_LANGUAGE", _DEFAULT_LANGUAGE)
    sys.stdout.write(f"preload_paddleocr: warming model cache (lang={language})\n")
    try:
        PaddleOCR(lang=language)
    except Exception as exc:
        sys.stdout.write(
            "preload_paddleocr: model warm-up failed "
            f"({type(exc).__name__}: {exc}); continuing image build.\n"
        )
        return 0
    sys.stdout.write("preload_paddleocr: model cache ready.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
