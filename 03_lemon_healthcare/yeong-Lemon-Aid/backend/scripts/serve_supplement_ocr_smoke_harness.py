"""Serve a local-only supplement OCR camera/upload smoke harness.

This operator tool is intentionally separate from the product API. It accepts a
single image, runs the configured local PaddleOCR adapter in request memory, and
returns raw OCR text only to the browser response so a tester can verify camera
or upload capture without changing public app contracts.
"""

from __future__ import annotations

import argparse
import html
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import HTMLResponse, JSONResponse

BACKEND_ROOT = Path(__file__).resolve().parents[1]
NUTRITION_BACKEND_ROOT = BACKEND_ROOT / "Nutrition-backend"
if str(NUTRITION_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(NUTRITION_BACKEND_ROOT))

from src.config import Settings  # noqa: E402
from src.ocr.base import OCRImageInput, OCRResult  # noqa: E402
from src.ocr.providers.paddle import PaddleOCRAdapter  # noqa: E402
from src.services.supplement_intake import (  # noqa: E402
    SupplementImageValidationError,
    ValidatedSupplementImage,
    read_and_validate_supplement_image,
)

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
DEFAULT_PORT = 8790

OCRAdapterFactory = Callable[[Settings], PaddleOCRAdapter]


@dataclass(frozen=True)
class ServerOptions:
    """Runtime options for the local smoke harness.

    Args:
        host: Host interface used by uvicorn.
        port: TCP port used by uvicorn.
        allow_non_loopback: Whether a non-loopback bind is explicitly allowed.
        confidence_threshold: Minimum local OCR confidence accepted by PaddleOCR.
    """

    host: str
    port: int
    allow_non_loopback: bool
    confidence_threshold: float


def main() -> None:
    """Run the OCR smoke harness server from CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--allow-non-loopback", action="store_true")
    parser.add_argument("--confidence-threshold", type=float, default=0.0)
    args = parser.parse_args()
    options = ServerOptions(
        host=args.host,
        port=args.port,
        allow_non_loopback=args.allow_non_loopback,
        confidence_threshold=args.confidence_threshold,
    )
    validate_server_options(options)

    uvicorn.run(
        create_app(confidence_threshold=options.confidence_threshold),
        host=options.host,
        port=options.port,
    )


def validate_server_options(options: ServerOptions) -> None:
    """Fail closed unless the server is loopback-bound or explicitly allowed.

    Args:
        options: Requested server options.

    Raises:
        SystemExit: If a non-loopback host was requested without opt-in.
    """
    if options.host in LOOPBACK_HOSTS or options.allow_non_loopback:
        return
    raise SystemExit(
        "Refusing non-loopback bind. Use --allow-non-loopback only behind a private tunnel."
    )


def create_app(
    *,
    confidence_threshold: float = 0.0,
    adapter_factory: OCRAdapterFactory = PaddleOCRAdapter,
) -> FastAPI:
    """Create the local OCR smoke FastAPI app.

    Args:
        confidence_threshold: Minimum local OCR confidence accepted by PaddleOCR.
        adapter_factory: Factory used to build the OCR adapter; tests inject a fake.

    Returns:
        FastAPI application serving the local harness.
    """
    settings = Settings(
        _env_file=None,
        ocr_primary_provider="paddleocr",
        enable_local_ocr=True,
        local_ocr_confidence_threshold=confidence_threshold,
    )
    app = FastAPI(title="Lemon Aid Local OCR Smoke Harness", docs_url=None, redoc_url=None)

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        """Return the camera/upload smoke harness page.

        Returns:
            HTML response for the local smoke UI.
        """
        return HTMLResponse(_html_page(), headers=_no_store_headers())

    @app.post("/api/ocr")
    async def run_ocr(image: Annotated[UploadFile, File()]) -> JSONResponse:
        """Run local OCR for one uploaded supplement-label image.

        Args:
            image: Operator-supplied label image from camera or file picker.

        Returns:
            JSON response containing transient OCR text and safe metadata.

        Raises:
            HTTPException: If image validation or OCR execution fails.
        """
        try:
            validated = await read_and_validate_supplement_image(image, settings)
        except SupplementImageValidationError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail={"code": exc.code, "message": exc.message},
            ) from exc

        ocr_input = OCRImageInput(
            image_bytes=validated.image_bytes,
            mime_type=validated.mime_type,
            width=validated.width,
            height=validated.height,
        )
        try:
            result = await adapter_factory(settings).extract_text(ocr_input)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "local_ocr_failed",
                    "message": str(exc) or "Local OCR failed.",
                },
            ) from exc

        return JSONResponse(_ocr_payload(result, validated), headers=_no_store_headers())

    return app


def _ocr_payload(result: OCRResult, validated: ValidatedSupplementImage) -> dict[str, object]:
    """Build the transient OCR response payload.

    Args:
        result: OCR provider result.
        validated: Validated upload metadata with width, height, MIME, and size.

    Returns:
        JSON-serializable OCR response.
    """
    text = result.text.strip()
    return {
        "status": "completed",
        "provider": result.provider,
        "confidence": result.confidence,
        "text": text,
        "line_count": len([line for line in text.splitlines() if line.strip()]),
        "image": {
            "mime_type": validated.mime_type,
            "size_bytes": validated.size_bytes,
            "width": validated.width,
            "height": validated.height,
        },
    }


def _no_store_headers() -> dict[str, str]:
    """Return headers that prevent local OCR result caching.

    Returns:
        HTTP headers for local-only transient responses.
    """
    return {
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
    }


def _html_page() -> str:
    """Return the self-contained smoke harness HTML.

    Returns:
        HTML document with camera/upload controls and OCR result rendering.
    """
    escaped_title = html.escape("Lemon Aid OCR Smoke")
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escaped_title}</title>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f6f7f9;
      color: #1f2933;
    }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: #f6f7f9;
    }}
    main {{
      width: min(980px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 24px 0 40px;
    }}
    h1 {{
      margin: 0 0 16px;
      font-size: 28px;
      font-weight: 700;
      letter-spacing: 0;
    }}
    .grid {{
      display: grid;
      grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
      gap: 16px;
      align-items: start;
    }}
    section {{
      background: #ffffff;
      border: 1px solid #d8dee6;
      border-radius: 8px;
      padding: 16px;
    }}
    label {{
      display: block;
      font-size: 14px;
      font-weight: 600;
      margin-bottom: 8px;
    }}
    input[type="file"] {{
      width: 100%;
      min-height: 44px;
    }}
    button {{
      width: 100%;
      min-height: 44px;
      margin-top: 12px;
      border: 0;
      border-radius: 8px;
      background: #0f766e;
      color: #ffffff;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
    }}
    button:disabled {{
      background: #94a3b8;
      cursor: progress;
    }}
    img {{
      display: none;
      width: 100%;
      max-height: 420px;
      object-fit: contain;
      border: 1px solid #d8dee6;
      border-radius: 8px;
      margin-top: 12px;
      background: #eef2f6;
    }}
    .status {{
      min-height: 24px;
      margin-top: 12px;
      font-size: 14px;
      color: #475569;
    }}
    pre {{
      min-height: 360px;
      margin: 0;
      padding: 12px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: #111827;
      color: #e5e7eb;
      border-radius: 8px;
      line-height: 1.45;
      font-size: 14px;
    }}
    .meta {{
      margin: 0 0 12px;
      color: #475569;
      font-size: 14px;
    }}
    @media (max-width: 760px) {{
      main {{
        width: min(100vw - 20px, 620px);
        padding-top: 16px;
      }}
      .grid {{
        grid-template-columns: 1fr;
      }}
      h1 {{
        font-size: 23px;
      }}
      pre {{
        min-height: 240px;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>Lemon Aid OCR Smoke</h1>
    <div class="grid">
      <section>
        <label for="image">Camera or image upload</label>
        <input id="image" name="image" type="file" accept="image/*" capture="environment">
        <button id="run" type="button">Run OCR</button>
        <div id="status" class="status">No image selected.</div>
        <img id="preview" alt="Selected supplement label preview">
      </section>
      <section>
        <p id="meta" class="meta">Provider, confidence, and text appear here after OCR.</p>
        <pre id="text"></pre>
      </section>
    </div>
  </main>
  <script>
    const input = document.getElementById('image');
    const button = document.getElementById('run');
    const status = document.getElementById('status');
    const preview = document.getElementById('preview');
    const text = document.getElementById('text');
    const meta = document.getElementById('meta');

    input.addEventListener('change', () => {{
      const file = input.files && input.files[0];
      if (!file) {{
        preview.style.display = 'none';
        status.textContent = 'No image selected.';
        return;
      }}
      preview.src = URL.createObjectURL(file);
      preview.style.display = 'block';
      status.textContent = `${{file.name || 'camera image'}} selected.`;
      text.textContent = '';
      meta.textContent = 'Ready to run local OCR.';
    }});

    button.addEventListener('click', async () => {{
      const file = input.files && input.files[0];
      if (!file) {{
        status.textContent = 'Select or capture an image first.';
        return;
      }}
      const form = new FormData();
      form.append('image', file);
      button.disabled = true;
      status.textContent = 'Running local PaddleOCR...';
      text.textContent = '';
      try {{
        const response = await fetch('/api/ocr', {{
          method: 'POST',
          headers: {{ 'ngrok-skip-browser-warning': 'true' }},
          body: form,
        }});
        const payload = await response.json();
        if (!response.ok) {{
          const detail = payload.detail || {{}};
          throw new Error(detail.message || detail.code || `HTTP ${{response.status}}`);
        }}
        meta.textContent = `Provider: ${{payload.provider}} | Confidence: ${{payload.confidence ?? 'n/a'}} | Lines: ${{payload.line_count}}`;
        text.textContent = payload.text || '(empty OCR text)';
        status.textContent = 'OCR completed. Text is shown only in this browser response.';
      }} catch (error) {{
        meta.textContent = 'OCR failed.';
        text.textContent = String(error);
        status.textContent = 'OCR failed.';
      }} finally {{
        button.disabled = false;
      }}
    }});
  </script>
</body>
</html>"""


if __name__ == "__main__":
    main()
