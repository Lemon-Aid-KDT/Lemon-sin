#!/usr/bin/env python3
"""실사 manifest 의 빈 gt_text 슬롯을 PaddleOCR multi 결과로 부트스트랩.

목적:
    사람 검수 작업의 부담을 줄이기 위해 OCR 1차 결과를 manifest 의 ``gt_text`` /
    ``gt_fields`` 슬롯에 미리 채워둔다. 사람은 빈 칸을 채우는 것이 아니라 OCR
    결과를 "수정·승인" 하면 된다.

⚠️ 안전 표시:
    부트스트랩된 항목은 ``labeled=false`` 로 남는다. 측정 코드(벤치마크 러너) 는
    ``labeled=true`` 인 항목만 사용해야 한다. OCR 이 자기 출력을 GT 로 측정하는
    오염을 막기 위해.

흐름:
    1. real_manifest.json 로드
    2. 각 item.image_path 로 이미지 로드
    3. MultilingualOCRAdapter (ko+en) 로 OCR 실행
    4. field_extractor 로 필드 추출
    5. manifest 의 ``gt_text`` / ``gt_fields`` 슬롯에 결과 기록
    6. ``labeled`` 값은 그대로 (기본 false). 이미 ``labeled=true`` 인 항목은 건드리지 않음.

사용:
    cd backend && source .venv/bin/activate
    python ../scripts/bootstrap_real_labels.py \\
        --manifest ../data/ocr_eval/real_manifest.json \\
        --data-root ../data/ocr_eval \\
        --adapter multi

Reference:
    backend/src/ocr/multilingual_adapter.py
    backend/src/ocr/field_extractor.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# scripts/ → backend/src 로의 경로 보장
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_REPO_ROOT / "backend"))

from src.ocr.base import OCRAdapter  # noqa: E402
from src.ocr.field_extractor import extract_fields  # noqa: E402
from src.ocr.preprocessor import preprocess_image  # noqa: E402


def _build_adapter(name: str, timeout_sec: float) -> OCRAdapter:
    """이름으로 어댑터 생성. PaddleOCR/Multi 만 지원."""
    from src.ocr.multilingual_adapter import MultilingualOCRAdapter  # noqa: PLC0415
    from src.ocr.paddleocr_adapter import PaddleOCRAdapter  # noqa: PLC0415

    if name == "paddleocr-ko":
        return PaddleOCRAdapter(lang="korean", timeout_sec=timeout_sec)
    if name == "paddleocr-en":
        return PaddleOCRAdapter(lang="en", timeout_sec=timeout_sec)
    if name == "multi":
        return MultilingualOCRAdapter(
            primary=PaddleOCRAdapter(lang="korean", timeout_sec=timeout_sec),
            secondary=PaddleOCRAdapter(lang="en", timeout_sec=timeout_sec),
        )
    raise ValueError(f"Unknown adapter: {name}")


_YOLO_DETECTOR: Any | None = None


async def _maybe_apply_roi(image_bytes: bytes, *, use_roi: bool) -> bytes:
    """선택적으로 YOLO ROI 크롭을 적용. 검출 실패/미설치 시 원본 반환.

    Detector 는 모듈 전역에 1회 캐싱 — 매 호출마다 모델 재로드 방지.
    """
    if not use_roi:
        return image_bytes
    try:
        from src.vision.yolo_label_detector import (  # noqa: PLC0415
            YoloLabelDetector,
            crop_to_roi,
            select_primary_region,
        )
    except ImportError:
        return image_bytes

    global _YOLO_DETECTOR
    if _YOLO_DETECTOR is None:
        _YOLO_DETECTOR = YoloLabelDetector()

    try:
        regions = await _YOLO_DETECTOR.detect_regions(image_bytes)
    except Exception:  # noqa: BLE001 — ROI 실패 시 원본
        return image_bytes
    primary = select_primary_region(regions)
    if primary is None:
        return image_bytes
    return crop_to_roi(image_bytes, primary)


async def _bootstrap(args: argparse.Namespace) -> int:
    """manifest 의 빈 슬롯을 OCR 결과로 채운다."""
    manifest_path: Path = args.manifest
    if not manifest_path.exists():
        sys.stderr.write(f"manifest not found: {manifest_path}\n")
        return 1

    data_root: Path = args.data_root
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = manifest.get("items", [])
    if not items:
        sys.stderr.write("manifest has no items\n")
        return 1

    adapter = _build_adapter(args.adapter, timeout_sec=args.timeout_sec)
    sys.stdout.write(
        f"Using adapter: {adapter.engine_name} "
        f"(timeout={args.timeout_sec}s, use_roi={args.use_roi})\n"
    )

    filled = 0
    skipped = 0
    failed = 0

    for item in items:
        if item.get("labeled"):
            skipped += 1
            continue
        if item.get("gt_text") and not args.force_refresh:
            # 이미 누가 채운 경우 — 덮어쓰지 않음 (사람 작업 보존)
            skipped += 1
            continue

        image_path = data_root / item["image_path"]
        if not image_path.exists():
            sys.stderr.write(f"image not found: {image_path}\n")
            failed += 1
            continue

        try:
            raw_bytes = image_path.read_bytes()
            # 실사 사진은 3000~4032px 고해상도라 PaddleOCR 30s timeout 초과.
            # 전처리(리사이즈 + RGB + EXIF strip) 거쳐서 OCR pipeline 과 동일 입력으로.
            preprocessed = preprocess_image(raw_bytes)
            # YOLO ROI 옵션 — 라벨/병 영역만 자르면 OCR 부담이 크게 줄어든다.
            roi_bytes = await _maybe_apply_roi(preprocessed, use_roi=args.use_roi)
            result = await adapter.extract_text(roi_bytes)
        except Exception as exc:  # noqa: BLE001 — bootstrap 도구는 best-effort
            sys.stderr.write(f"OCR failed for {item['id']}: {exc}\n")
            failed += 1
            continue

        item["gt_text"] = result.text
        item["gt_fields"] = extract_fields(result.text)
        item["bootstrap_engine"] = result.engine
        item["bootstrap_confidence"] = result.confidence
        # labeled 는 의도적으로 false 로 유지 — 사람 검수 표시.
        item["labeled"] = False
        filled += 1
        sys.stdout.write(
            f"  [{item['id']}] {result.engine} conf={result.confidence:.3f} "
            f"chars={len(result.text)}\n"
        )

    manifest["labeled_count"] = sum(1 for it in items if it.get("labeled"))
    manifest["bootstrap_count"] = sum(1 for it in items if it.get("bootstrap_engine"))

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    sys.stdout.write(
        f"\nBootstrapped {filled} items (skipped {skipped}, failed {failed}).\n"
        f"Manifest updated: {manifest_path}\n"
        "  → 다음 단계: 사람이 각 item.gt_text / gt_fields 를 검수·수정 후 labeled=true 로 변경\n"
    )
    return 0 if failed == 0 else 2


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """CLI 인자 파싱."""
    parser = argparse.ArgumentParser(
        description="실사 manifest 의 빈 gt_text 를 OCR 결과로 부트스트랩합니다."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="real_manifest.json 경로",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        required=True,
        help="이미지 파일들의 베이스 디렉터리 (manifest 의 image_path 가 상대경로)",
    )
    parser.add_argument(
        "--adapter",
        choices=["paddleocr-ko", "paddleocr-en", "multi"],
        default="multi",
        help="부트스트랩에 사용할 어댑터 (default: multi)",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="이미 gt_text 가 있어도 OCR 재실행. labeled=true 항목은 보호된다.",
    )
    parser.add_argument(
        "--use-roi",
        action="store_true",
        help="YOLO 로 라벨/병 영역만 잘라 OCR. 고해상도 실사 사진의 timeout 회피.",
    )
    parser.add_argument(
        "--timeout-sec",
        type=float,
        default=60.0,
        help="단일 OCR 호출 timeout(초). 기본 60 (실사 4K 사진 대응).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """엔트리 포인트."""
    args = parse_args(argv)
    return asyncio.run(_bootstrap(args))


if __name__ == "__main__":
    raise SystemExit(main())
