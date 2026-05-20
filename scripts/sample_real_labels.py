#!/usr/bin/env python3
"""실사 영양제 라벨 이미지 샘플링 + 라벨링 워크플로 manifest 생성기.

외장 드라이브의 카테고리별 영양제 사진에서 N장씩 결정론적으로 골라
``data/ocr_eval/real_samples/`` 로 복사하고 ``real_manifest.json`` 의 빈
``gt_text`` / ``gt_fields`` 슬롯을 만든다. 사람이 manifest 를 열어 정답을
채우면 그대로 benchmark runner 가 소비할 수 있다.

manifest 스키마는 ``synth_label_dataset.py`` 와 동일하나 ``kind="real"`` 이며
처음에는 ``gt_text=""`` / ``gt_fields=None`` 으로 비어 있다. 라벨링 시 채워
넣을 것.

사용:
    ./scripts/sample_real_labels.py \\
        --source "/Volumes/Corsair EX300U Media/00_work_out/00_data_set/pr/downloads_tampermonkey/lemon-aid/_inbox/tampermonkey/naver" \\
        --per-category 5 \\
        --output data/ocr_eval/real_samples \\
        --manifest data/ocr_eval/real_manifest.json \\
        --seed 42

외장 드라이브가 마운트되어 있지 않으면 즉시 정상 종료한다 (CI/다른 머신 안전).

Reference:
    scripts/synth_label_dataset.py
    backend/tests/e2e/test_ocr_accuracy.py
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

DEFAULT_PER_CATEGORY: Final[int] = 5
DEFAULT_OUTPUT_DIR: Final[Path] = Path("data/ocr_eval/real_samples")
DEFAULT_MANIFEST: Final[Path] = Path("data/ocr_eval/real_manifest.json")
DEFAULT_SEED: Final[int] = 42
IMAGE_EXTENSIONS: Final[tuple[str, ...]] = (".jpg", ".jpeg", ".png", ".webp")


@dataclass(frozen=True)
class SampledImage:
    """샘플링 결과 한 장.

    Attributes:
        item_id: ``real_<category>_<idx>``.
        category: 외장 드라이브 폴더명 (예: ``[비타민C]``).
        source_path: 원본 파일의 절대 경로.
        relative_dest: manifest 의 ``image_path`` 로 쓸 상대 경로.
    """

    item_id: str
    category: str
    source_path: Path
    relative_dest: Path


def _list_categories(source_root: Path) -> list[Path]:
    """source_root 직속 서브디렉터리 (카테고리) 목록을 반환.

    Args:
        source_root: 외장 드라이브의 ``.../naver`` 경로.

    Returns:
        카테고리 디렉터리 목록 (이름 정렬).
    """
    return sorted(p for p in source_root.iterdir() if p.is_dir())


def _list_images(category_dir: Path) -> list[Path]:
    """카테고리 폴더 내 모든 이미지 파일 (재귀 탐색).

    Args:
        category_dir: 카테고리 디렉터리.

    Returns:
        이미지 파일 경로 목록 (이름 정렬).
    """
    return sorted(
        p
        for p in category_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )


def _slugify_category(name: str) -> str:
    """폴더명에서 manifest id 용 안전 슬러그 생성.

    Args:
        name: 원본 카테고리명 (예: ``[비타민C]``).

    Returns:
        ascii-safe 슬러그. 한글은 보존하되 ``[`` ``]`` ``/`` 같은 특수문자 제거.
    """
    return (
        name.replace("[", "")
        .replace("]", "")
        .replace(" ", "_")
        .replace("/", "_")
        .strip("_")
        or "uncategorized"
    )


def _sample_per_category(
    source_root: Path,
    per_category: int,
    rng: random.Random,
) -> list[SampledImage]:
    """카테고리마다 ``per_category`` 장씩 샘플링.

    Args:
        source_root: 외장 드라이브의 ``.../naver`` 경로.
        per_category: 카테고리당 샘플 수.
        rng: 시드된 RNG.

    Returns:
        샘플 결과 목록.
    """
    samples: list[SampledImage] = []
    for category_dir in _list_categories(source_root):
        images = _list_images(category_dir)
        if not images:
            continue
        chosen = rng.sample(images, k=min(per_category, len(images)))
        slug = _slugify_category(category_dir.name)
        for idx, src in enumerate(chosen):
            item_id = f"real_{slug}_{idx + 1:03d}"
            ext = src.suffix.lower()
            relative_dest = Path("real_samples") / slug / f"{item_id}{ext}"
            samples.append(
                SampledImage(
                    item_id=item_id,
                    category=category_dir.name,
                    source_path=src,
                    relative_dest=relative_dest,
                )
            )
    return samples


def _write_manifest(
    samples: list[SampledImage],
    manifest_path: Path,
    seed: int,
    source_root: Path,
    per_category: int,
) -> None:
    """샘플 목록을 JSON manifest 로 직렬화.

    Args:
        samples: 샘플 결과.
        manifest_path: 출력 JSON 경로.
        seed: 시드 값 (재현성 메타데이터).
        source_root: 원본 루트 경로 (메타데이터).
        per_category: 카테고리당 샘플 수 (메타데이터).
    """
    items = [
        {
            "id": s.item_id,
            "image_path": str(s.relative_dest),
            "language": "unknown",
            "source_path": str(s.source_path),
            "category": s.category,
            "gt_text": "",
            "gt_fields": None,
            "labeled": False,
        }
        for s in samples
    ]
    manifest = {
        "version": 1,
        "kind": "real",
        "seed": seed,
        "source_root": str(source_root),
        "per_category": per_category,
        "count": len(items),
        "labeled_count": 0,
        "items": items,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> int:
    """샘플링·복사·manifest 생성 메인 흐름.

    Args:
        args: argparse 결과.

    Returns:
        프로세스 종료 코드.
    """
    source_root: Path = args.source
    if not source_root.exists():
        sys.stderr.write(
            f"[skip] Source root not mounted: {source_root}\n"
            "       External drive may not be connected. Exiting gracefully.\n"
        )
        return 0

    categories = _list_categories(source_root)
    if not categories:
        sys.stderr.write(f"No category folders found under {source_root}\n")
        return 1

    rng = random.Random(args.seed)
    samples = _sample_per_category(source_root, args.per_category, rng)
    if not samples:
        sys.stderr.write("No images sampled (categories empty?)\n")
        return 1

    output_root: Path = args.output
    output_root.mkdir(parents=True, exist_ok=True)

    for sample in samples:
        dest = output_root.parent / sample.relative_dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(sample.source_path, dest)
        except OSError as exc:
            sys.stderr.write(f"Failed to copy {sample.source_path}: {exc}\n")
            return 2

    _write_manifest(
        samples=samples,
        manifest_path=args.manifest,
        seed=args.seed,
        source_root=source_root,
        per_category=args.per_category,
    )

    sys.stdout.write(
        f"Sampled {len(samples)} images across {len(categories)} categories.\n"
        f"Copied to {output_root.parent}\n"
        f"Manifest written to {args.manifest}\n"
        "  → 다음 단계: manifest 의 각 item.gt_text / gt_fields 를 사람이 채우세요.\n"
    )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """CLI 인자 파싱.

    Args:
        argv: 명시적 argv.

    Returns:
        argparse.Namespace.
    """
    parser = argparse.ArgumentParser(
        description="외장 드라이브의 카테고리별 영양제 이미지에서 K장씩 샘플링합니다."
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="외장 드라이브의 카테고리 루트 경로",
    )
    parser.add_argument(
        "--per-category",
        type=int,
        default=DEFAULT_PER_CATEGORY,
        help=f"카테고리당 샘플 수 (default: {DEFAULT_PER_CATEGORY})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"이미지 복사 디렉터리 (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help=f"manifest JSON 경로 (default: {DEFAULT_MANIFEST})",
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
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
