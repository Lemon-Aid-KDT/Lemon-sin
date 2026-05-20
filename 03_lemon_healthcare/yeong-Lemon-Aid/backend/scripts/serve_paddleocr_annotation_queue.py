"""Serve a local-only PaddleOCR annotation queue and write verified manifests.

This script intentionally stays local-only. It serves copied private queue
images from ``--queue-dir`` and accepts human-verified box/transcript JSON. The
saved manifest uses the existing PaddleOCRFineTuningSample schema so the
exporter can produce official PaddleOCR detection and recognition label files.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from hashlib import sha256
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast

BACKEND_ROOT = Path(__file__).resolve().parents[1]
NUTRITION_BACKEND_ROOT = BACKEND_ROOT / "Nutrition-backend"
if str(NUTRITION_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(NUTRITION_BACKEND_ROOT))

from src.learning.consent_gate import IMAGE_LEARNING_REQUIRED_CONSENTS  # noqa: E402
from src.learning.paddleocr_finetuning import (  # noqa: E402
    PaddleOCRFineTuningExportError,
    reject_raw_manifest_fields,
)
from src.models.schemas.paddleocr_finetuning import (  # noqa: E402
    PaddleOCRFineTuningSample,
)

QUEUE_SCHEMA_VERSION = "paddleocr-annotation-queue-v1"
VERIFIED_MANIFEST_SCHEMA_VERSION = "paddleocr-finetuning-manifest-v1"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


class AnnotationQueueError(ValueError):
    """Raised when human annotation payloads are unsafe or invalid."""


def main() -> None:
    """Run the local annotation queue HTTP server."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue-dir", required=True, type=Path)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", default=DEFAULT_PORT, type=int)
    args = parser.parse_args()

    queue = load_annotation_queue(args.queue_dir)
    if not queue["items"]:
        raise AnnotationQueueError("Annotation queue has no items.")
    server = build_annotation_server(
        queue_dir=args.queue_dir,
        queue=queue,
        host=args.host,
        port=args.port,
    )
    print(f"Serving local PaddleOCR annotation queue at http://{args.host}:{args.port}")
    server.serve_forever()


def load_annotation_queue(queue_dir: Path) -> dict[str, Any]:
    """Load and validate a prepared annotation queue.

    Args:
        queue_dir: Queue directory containing annotation_queue.json.

    Returns:
        Queue payload.

    Raises:
        AnnotationQueueError: If the queue is missing or malformed.
    """
    queue_path = queue_dir / "annotation_queue.json"
    if not queue_path.exists():
        raise AnnotationQueueError(f"Queue file not found: {queue_path}")
    payload = json.loads(queue_path.read_text(encoding="utf-8"))
    reject_raw_manifest_fields(payload)
    if payload.get("schema_version") != QUEUE_SCHEMA_VERSION:
        raise AnnotationQueueError("Unsupported annotation queue schema version.")
    items = payload.get("items")
    if not isinstance(items, list):
        raise AnnotationQueueError("Annotation queue must contain an items list.")
    for item in items:
        _validate_queue_item(item)
    return cast(dict[str, Any], payload)


def annotation_to_samples(
    *,
    queue_item: dict[str, Any],
    annotation: dict[str, Any],
) -> list[dict[str, Any]]:
    """Convert one human annotation payload into fine-tuning samples.

    Args:
        queue_item: Prepared queue item metadata.
        annotation: Human-verified annotation payload.

    Returns:
        List of schema-validated sample dictionaries.

    Raises:
        AnnotationQueueError: If the annotation is not explicitly verified.
    """
    reject_raw_manifest_fields(annotation)
    if annotation.get("queue_id") != queue_item["queue_id"]:
        raise AnnotationQueueError("Annotation queue_id does not match queue item.")
    if annotation.get("human_verified") is not True:
        raise AnnotationQueueError("Only human_verified=true annotations can be exported.")

    language_mix = annotation.get("language_mix", "ko_en")
    field_type = annotation.get("field_type", "other")
    badcase_categories = annotation.get("badcase_categories", [])
    quality_labels = sorted(
        set(queue_item.get("quality_labels", [])) | set(annotation.get("quality_labels", []))
    )
    samples: list[dict[str, Any]] = []

    boxes = annotation.get("boxes", [])
    if boxes:
        detection_dict = _base_sample_dict(
            queue_item=queue_item,
            annotation=annotation,
            sample_suffix="det-000",
            task_type="detection",
            transcript_material=json.dumps(boxes, ensure_ascii=False, sort_keys=True),
            language_mix=language_mix,
            field_type=field_type,
            badcase_categories=badcase_categories,
            quality_labels=quality_labels,
        )
        detection_dict["boxes"] = [_normalize_box(box) for box in boxes]
        PaddleOCRFineTuningSample.model_validate(detection_dict)
        samples.append(detection_dict)

    transcripts = annotation.get("recognition_transcripts", [])
    if isinstance(transcripts, str):
        transcripts = [transcripts]
    if not isinstance(transcripts, list):
        raise AnnotationQueueError("recognition_transcripts must be a string or list.")
    for index, transcript in enumerate(transcripts):
        if not isinstance(transcript, str) or not transcript.strip():
            raise AnnotationQueueError("Recognition transcript must be non-empty text.")
        normalized_transcript = transcript.strip()
        recognition_dict = _base_sample_dict(
            queue_item=queue_item,
            annotation=annotation,
            sample_suffix=f"rec-{index:03d}",
            task_type="recognition",
            transcript_material=normalized_transcript,
            language_mix=language_mix,
            field_type=field_type,
            badcase_categories=badcase_categories,
            quality_labels=quality_labels,
        )
        recognition_dict["verified_transcript"] = normalized_transcript
        PaddleOCRFineTuningSample.model_validate(recognition_dict)
        samples.append(recognition_dict)

    if not samples:
        raise AnnotationQueueError("Annotation must contain at least one box or transcript.")
    return samples


def write_verified_manifest(
    *,
    queue_dir: Path,
    annotations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Write a private human-verified manifest for the exporter.

    Args:
        queue_dir: Queue directory.
        annotations: Human annotation payloads.

    Returns:
        Redacted summary with output path and sample count.
    """
    queue = load_annotation_queue(queue_dir)
    queue_by_id = {item["queue_id"]: item for item in queue["items"]}
    samples: list[dict[str, Any]] = []
    for annotation in annotations:
        queue_id = annotation.get("queue_id")
        if queue_id not in queue_by_id:
            raise AnnotationQueueError(f"Unknown queue_id: {queue_id}")
        samples.extend(
            annotation_to_samples(queue_item=queue_by_id[queue_id], annotation=annotation)
        )

    manifest = {
        "schema_version": VERIFIED_MANIFEST_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "items": samples,
    }
    reject_raw_manifest_fields(manifest)
    output_path = queue_dir / "verified_manifest.json"
    output_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "manifest_path": str(output_path),
        "sample_count": len(samples),
        "raw_ocr_text_stored": False,
        "provider_payload_stored": False,
        "api_credentials_stored": False,
    }


def build_annotation_server(
    *,
    queue_dir: Path,
    queue: dict[str, Any],
    host: str,
    port: int,
) -> ThreadingHTTPServer:
    """Build a local HTTP server for the annotation queue.

    Args:
        queue_dir: Queue directory.
        queue: Loaded queue payload.
        host: Bind host.
        port: Bind port.

    Returns:
        HTTP server.
    """

    class AnnotationHandler(SimpleHTTPRequestHandler):
        """HTTP handler scoped to one queue directory."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(queue_dir), **kwargs)

        def do_GET(self) -> None:
            """Serve queue metadata, images, and static HTML."""
            if self.path == "/api/queue":
                self._send_json(queue)
                return
            if self.path in {"/", "/annotation_queue.html"}:
                self.path = "/annotation_queue.html"
            super().do_GET()

        def do_POST(self) -> None:
            """Accept human-verified annotation JSON."""
            if self.path != "/api/annotations":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                annotations = payload if isinstance(payload, list) else [payload]
                summary = write_verified_manifest(queue_dir=queue_dir, annotations=annotations)
            except (
                AnnotationQueueError,
                PaddleOCRFineTuningExportError,
                json.JSONDecodeError,
            ) as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            self._send_json(summary)

        def _send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ThreadingHTTPServer((host, port), AnnotationHandler)


def _base_sample_dict(
    *,
    queue_item: dict[str, Any],
    annotation: dict[str, Any],
    sample_suffix: str,
    task_type: str,
    transcript_material: str,
    language_mix: str,
    field_type: str,
    badcase_categories: list[str],
    quality_labels: list[str],
) -> dict[str, Any]:
    sample_id = f"{queue_item['queue_id']}-{sample_suffix}"
    return {
        "sample_id": sample_id,
        "source_image_id": queue_item["source_image_id"],
        "crop_id": annotation.get("crop_id", f"{queue_item['queue_id']}-full-image"),
        "image_path": queue_item["image_path"],
        "product_group_id": queue_item["product_group_id"],
        "image_hash": queue_item["image_sha256"],
        "split_group": queue_item["split_group"],
        "split": queue_item["split"],
        "task_type": task_type,
        "language_mix": language_mix,
        "field_type": field_type,
        "human_verified": True,
        "consent_scope": [consent.value for consent in IMAGE_LEARNING_REQUIRED_CONSENTS],
        "transcript_hash": sha256(transcript_material.encode("utf-8")).hexdigest(),
        "session_group_id": annotation.get("session_group_id"),
        "source_provider": annotation.get("source_provider", "human_verified"),
        "badcase_categories": badcase_categories,
        "quality_labels": quality_labels,
        "synthetic": False,
    }


def _normalize_box(box: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(box, dict):
        raise AnnotationQueueError("Detection box must be an object.")
    transcription = box.get("transcription")
    if box.get("ignore") is True:
        transcription = "###"
    if not isinstance(transcription, str) or not transcription.strip():
        raise AnnotationQueueError("Detection box transcription must be non-empty.")
    points = box.get("points")
    if not isinstance(points, list):
        raise AnnotationQueueError("Detection box points must be a list.")
    return {
        "transcription": transcription.strip(),
        "points": points,
        "ignore": bool(box.get("ignore", False)),
    }


def _validate_queue_item(item: object) -> None:
    if not isinstance(item, dict):
        raise AnnotationQueueError("Queue item must be an object.")
    required = {
        "queue_id",
        "source_image_id",
        "image_path",
        "image_sha256",
        "product_group_id",
        "split_group",
        "split",
    }
    missing = sorted(required.difference(item))
    if missing:
        raise AnnotationQueueError(f"Queue item missing required fields: {missing}")
    if item.get("human_verified") is not False:
        raise AnnotationQueueError("Prepared queue items must start with human_verified=false.")


if __name__ == "__main__":
    main()
