#!/usr/bin/env python3
"""합성 영양제 라벨 이미지 + manifest 생성기 — OCR 정확도 베이스라인용.

KDRIs / MFDS 영양소 사전을 시드 삼아 한·영·혼합 라벨 이미지를 결정론적으로
생성한다. 생성된 데이터셋은 ``tests/e2e/test_ocr_accuracy.py`` 의 benchmark
runner 가 그대로 소비할 수 있는 manifest 스키마를 따른다.

스키마:
    {
      "version": 1,
      "items": [
        {
          "id": "synth_0001",
          "image_path": "synthetic/synth_0001.jpg",  # manifest 상대 경로
          "language": "ko" | "en" | "mixed",
          "gt_text": "<라인 합친 전체 텍스트>",
          "gt_fields": {
            "product_name": "...",
            "ingredients": ["...", "..."],
            "dosage": "1000mg"
          }
        }
      ]
    }

사용:
    ./scripts/synth_label_dataset.py --count 60 \\
        --output data/ocr_eval/synthetic \\
        --manifest data/ocr_eval/synthetic_manifest.json \\
        --seed 42

Reference:
    backend/src/ocr/metrics.py
    docs/dev-guides/07-ocr-pipeline.md §7
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from PIL import Image, ImageDraw, ImageFont

DEFAULT_KDRIS_CSV: Final[Path] = Path("data/kdris/kdris_2020.csv")
DEFAULT_MFDS_CSV: Final[Path] = Path("data/mfds/functional_ingredients.csv")
DEFAULT_OUTPUT_DIR: Final[Path] = Path("data/ocr_eval/synthetic")
DEFAULT_MANIFEST: Final[Path] = Path("data/ocr_eval/synthetic_manifest.json")
DEFAULT_COUNT: Final[int] = 60
DEFAULT_SEED: Final[int] = 42

# macOS 기본 폰트 (system) — 한·영 모두 안정적으로 렌더.
KOREAN_FONT_CANDIDATES: Final[list[str]] = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/Users/yeong/Library/Fonts/NanumGothic.ttf",
    "/Users/yeong/Library/Fonts/NanumSquareEB.ttf",
]
ENGLISH_FONT_CANDIDATES: Final[list[str]] = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/Library/Fonts/Arial.ttf",
]

IMAGE_WIDTH: Final[int] = 720
IMAGE_HEIGHT: Final[int] = 960
MARGIN: Final[int] = 48
TITLE_FONT_SIZE: Final[int] = 42
BODY_FONT_SIZE: Final[int] = 28
LINE_SPACING: Final[int] = 16


@dataclass(frozen=True)
class Nutrient:
    """KDRIs/MFDS row 로부터 합성된 영양소.

    Attributes:
        code: KDRIs 코드 (예: ``vitamin_c_mg``).
        name_ko: 한국어 이름.
        name_en: 영어 이름.
        unit: 단위 (mg, μg 등).
    """

    code: str
    name_ko: str
    name_en: str
    unit: str


def load_nutrients(kdris_csv: Path) -> list[Nutrient]:
    """KDRIs CSV → ``Nutrient`` 목록 (코드 단위 dedup).

    Args:
        kdris_csv: KDRIs 기준치 CSV 경로.

    Returns:
        고유 영양소 목록 (성·연령별 row 중첩 제거).

    Raises:
        FileNotFoundError: CSV 가 없는 경우.
    """
    if not kdris_csv.exists():
        raise FileNotFoundError(f"KDRIs CSV not found: {kdris_csv}")

    seen: dict[str, Nutrient] = {}
    with kdris_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row["code"]
            if code in seen:
                continue
            seen[code] = Nutrient(
                code=code,
                name_ko=row["name_ko"],
                name_en=row["name_en"],
                unit=row["unit"],
            )
    return list(seen.values())


def find_first_existing(paths: list[str]) -> str | None:
    """후보 파일 경로 중 처음 존재하는 것을 반환.

    Args:
        paths: 절대 경로 후보 목록.

    Returns:
        존재하는 첫 경로 또는 ``None``.
    """
    for p in paths:
        if Path(p).exists():
            return p
    return None


def _load_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    """폰트 로드 헬퍼.

    Args:
        font_path: TTF/TTC 절대 경로.
        size: 폰트 크기 (px).

    Returns:
        FreeTypeFont 객체.
    """
    return ImageFont.truetype(font_path, size=size)


def _random_dosage(rng: random.Random, unit: str) -> tuple[int, str]:
    """단위에 맞는 자연스러운 함량 값 생성.

    Args:
        rng: 시드된 RNG.
        unit: 영양소 단위.

    Returns:
        ``(amount, formatted_dosage)`` 튜플. e.g., ``(1000, "1000mg")``.
    """
    if "mg" in unit:
        amount = rng.choice([100, 200, 500, 1000, 1500, 2000])
    elif "μg" in unit or "ug" in unit.lower():
        amount = rng.choice([10, 25, 50, 100, 200, 400])
    else:
        amount = rng.choice([5, 10, 20, 50, 100])
    return amount, f"{amount}{unit}"


def _compose_label_lines(
    rng: random.Random,
    nutrients: list[Nutrient],
    language: str,
) -> tuple[list[str], dict[str, object]]:
    """라벨에 들어갈 줄 단위 텍스트와 GT 필드를 생성.

    Args:
        rng: 시드된 RNG.
        nutrients: 영양소 후보 목록.
        language: ``"ko"`` / ``"en"`` / ``"mixed"``.

    Returns:
        ``(lines, gt_fields)`` 튜플.
    """
    chosen = rng.sample(nutrients, k=rng.randint(3, 5))
    headline_nutrient = chosen[0]

    if language == "ko":
        product_name = f"{headline_nutrient.name_ko} 종합 영양제"
        header_lines = ["영양 정보", product_name]
        ingredient_label = "성분"
    elif language == "en":
        product_name = f"{headline_nutrient.name_en} Complex"
        header_lines = ["Nutrition Facts", product_name]
        ingredient_label = "Ingredients"
    else:  # mixed
        product_name = f"{headline_nutrient.name_ko} / {headline_nutrient.name_en}"
        header_lines = ["영양 정보 / Nutrition Facts", product_name]
        ingredient_label = "성분 Ingredients"

    ingredient_lines: list[str] = []
    ingredient_field: list[str] = []
    dosage_field: str | None = None

    for nutrient in chosen:
        amount, dosage = _random_dosage(rng, nutrient.unit)
        if language == "ko":
            name = nutrient.name_ko
        elif language == "en":
            name = nutrient.name_en
        else:
            name = f"{nutrient.name_ko} ({nutrient.name_en})"
        ingredient_lines.append(f"- {name}: {dosage}")
        ingredient_field.append(name)
        if dosage_field is None:
            dosage_field = dosage

    body_lines: list[str] = [*header_lines, "", ingredient_label, *ingredient_lines]
    gt_fields: dict[str, object] = {
        "product_name": product_name,
        "ingredients": ingredient_field,
        "dosage": dosage_field,
    }
    return body_lines, gt_fields


def render_label_image(
    lines: list[str],
    language: str,
    output_path: Path,
    *,
    korean_font: str | None,
    english_font: str | None,
) -> None:
    """라인 목록을 720×960 JPEG 라벨로 렌더한다.

    Args:
        lines: 줄 단위 텍스트.
        language: ``"ko"`` / ``"en"`` / ``"mixed"``.
        output_path: 저장할 JPG 경로.
        korean_font: 한글이 포함될 경우 사용할 폰트 경로.
        english_font: 영문 전용일 때 사용할 폰트 경로.

    Raises:
        RuntimeError: 적절한 폰트를 찾지 못한 경우.
    """
    use_korean_font = language in ("ko", "mixed") or korean_font is not None
    font_path = korean_font if use_korean_font else english_font
    if font_path is None:
        if korean_font is not None:
            font_path = korean_font
        elif english_font is not None:
            font_path = english_font
    if font_path is None:
        raise RuntimeError("No usable font found for synthesis")

    title_font = _load_font(font_path, TITLE_FONT_SIZE)
    body_font = _load_font(font_path, BODY_FONT_SIZE)

    image = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    y = MARGIN
    for idx, line in enumerate(lines):
        font = title_font if idx < 2 else body_font
        draw.text((MARGIN, y), line, fill=(20, 20, 20), font=font)
        bbox = draw.textbbox((MARGIN, y), line, font=font)
        line_height = bbox[3] - bbox[1]
        y += line_height + LINE_SPACING

    image.save(output_path, format="JPEG", quality=92, optimize=True)


def build_dataset(args: argparse.Namespace) -> int:
    """합성 데이터셋을 생성하고 manifest 파일을 기록한다.

    Args:
        args: argparse 결과.

    Returns:
        프로세스 종료 코드 (성공 시 0).
    """
    nutrients = load_nutrients(args.kdris_csv)
    if len(nutrients) < 5:
        sys.stderr.write(f"Need >=5 nutrients to synthesize, got {len(nutrients)}\n")
        return 1

    korean_font = find_first_existing(KOREAN_FONT_CANDIDATES)
    english_font = find_first_existing(ENGLISH_FONT_CANDIDATES)
    if korean_font is None and english_font is None:
        sys.stderr.write("No Korean nor English fonts found on host.\n")
        return 2

    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)
    items: list[dict[str, object]] = []
    languages = ["ko", "en", "mixed"]

    for i in range(args.count):
        item_id = f"synth_{i + 1:04d}"
        language = languages[i % len(languages)]
        lines, gt_fields = _compose_label_lines(rng, nutrients, language)

        image_filename = f"{item_id}.jpg"
        image_path = output_dir / image_filename

        try:
            render_label_image(
                lines,
                language,
                image_path,
                korean_font=korean_font,
                english_font=english_font,
            )
        except OSError as exc:
            sys.stderr.write(f"Failed to render {item_id}: {exc}\n")
            return 3

        manifest_relative = Path("synthetic") / image_filename
        items.append(
            {
                "id": item_id,
                "image_path": str(manifest_relative),
                "language": language,
                "gt_text": "\n".join(lines),
                "gt_fields": gt_fields,
            }
        )

    manifest = {
        "version": 1,
        "kind": "synthetic",
        "seed": args.seed,
        "count": len(items),
        "items": items,
    }
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    sys.stdout.write(
        f"Generated {len(items)} synthetic labels at {output_dir}\n"
        f"Manifest written to {args.manifest}\n"
    )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """CLI 인자 파싱.

    Args:
        argv: 테스트에서 명시적 argv 주입용. ``None`` 이면 ``sys.argv``.

    Returns:
        argparse.Namespace.
    """
    parser = argparse.ArgumentParser(
        description="합성 영양제 라벨 이미지와 manifest 를 생성합니다."
    )
    parser.add_argument(
        "--kdris-csv",
        type=Path,
        default=DEFAULT_KDRIS_CSV,
        help=f"KDRIs CSV 경로 (default: {DEFAULT_KDRIS_CSV})",
    )
    parser.add_argument(
        "--mfds-csv",
        type=Path,
        default=DEFAULT_MFDS_CSV,
        help=f"MFDS CSV 경로 (default: {DEFAULT_MFDS_CSV})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"이미지 출력 디렉터리 (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help=f"manifest JSON 경로 (default: {DEFAULT_MANIFEST})",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_COUNT,
        help=f"생성할 라벨 수 (default: {DEFAULT_COUNT})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"RNG 시드 (default: {DEFAULT_SEED})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """엔트리 포인트.

    Args:
        argv: 명시적 argv (테스트 용도).

    Returns:
        종료 코드.
    """
    args = parse_args(argv)
    return build_dataset(args)


if __name__ == "__main__":
    raise SystemExit(main())
