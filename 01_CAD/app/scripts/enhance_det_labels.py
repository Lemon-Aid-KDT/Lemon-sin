#!/usr/bin/env python3
"""
YOLOv8-det 라벨 자동 강화 스크립트

픽셀 분석 기반으로 도면 이미지의 텍스트 영역을 자동 탐지하여
기존 휴리스틱 라벨(title_block만 있음)을 강화한다.

MiSUMi/Unit_bearing 도면 공통 패턴:
  - 좌하단: 부품번호 텍스트 (title_block)
  - 상단~중앙: CAD 도형 (도면 본체)
  - 도형 주변: 치수 주석 (dimension_area) — 있는 경우

동작 원리:
  1. 이미지를 그레이스케일로 변환
  2. 밝은 픽셀(텍스트/선분)을 이진화
  3. Connected Component 분석으로 텍스트 클러스터 검출
  4. 클러스터 위치와 크기로 title_block / dimension_area 분류
  5. YOLO 라벨 파일 업데이트

사용법:
  python scripts/enhance_det_labels.py --dataset ./data/det_dataset
  python scripts/enhance_det_labels.py --dataset ./data/det_dataset --split train --preview 10
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image


# 탐지 클래스
DET_CLASSES = ["title_block", "dimension_area", "parts_table"]
DET_CLASS_MAP = {name: idx for idx, name in enumerate(DET_CLASSES)}


# ─────────────────────────────────────────────
# 픽셀 분석 함수
# ─────────────────────────────────────────────

def analyze_image_regions(
    image_path: Path,
    bright_threshold: int = 180,
    min_cluster_area: int = 200,
    dark_bg: bool = True,
) -> list[dict]:
    """이미지의 밝은 영역(텍스트/선분)을 분석하여 클러스터를 반환한다.

    Args:
        image_path: 이미지 경로
        bright_threshold: 밝은 픽셀 임계값 (0~255)
        min_cluster_area: 최소 클러스터 면적 (픽셀)
        dark_bg: 어두운 배경 여부 (True: CAD 도면 스타일)

    Returns:
        [{"bbox": (x1,y1,x2,y2), "area": int, "density": float, "is_text_like": bool}, ...]
    """
    try:
        img = Image.open(image_path).convert("L")  # 그레이스케일
    except Exception:
        return []

    arr = np.array(img)
    h, w = arr.shape

    # 이진화: 밝은 픽셀 = 1 (텍스트/선분)
    if dark_bg:
        binary = (arr > bright_threshold).astype(np.uint8)
    else:
        binary = (arr < (255 - bright_threshold)).astype(np.uint8)

    # 간단한 Connected Component 분석 (scipy 없이 구현)
    clusters = _find_clusters_grid(binary, grid_size=32, min_density=0.01)

    # 면적 필터
    result = []
    for cl in clusters:
        area = (cl["bbox"][2] - cl["bbox"][0]) * (cl["bbox"][3] - cl["bbox"][1])
        if area >= min_cluster_area:
            cl["area"] = area
            cl["img_size"] = (w, h)
            result.append(cl)

    return result


def _find_clusters_grid(
    binary: np.ndarray,
    grid_size: int = 32,
    min_density: float = 0.01,
) -> list[dict]:
    """그리드 기반으로 밝은 픽셀 클러스터를 찾는다.

    이미지를 grid_size 단위로 분할하여 각 셀의 밝은 픽셀 비율을 계산하고,
    인접한 활성 셀을 병합하여 클러스터를 구성한다.
    """
    h, w = binary.shape
    rows = (h + grid_size - 1) // grid_size
    cols = (w + grid_size - 1) // grid_size

    # 각 그리드 셀의 밝은 픽셀 밀도 계산
    grid = np.zeros((rows, cols), dtype=np.float32)
    for r in range(rows):
        for c in range(cols):
            y1 = r * grid_size
            y2 = min((r + 1) * grid_size, h)
            x1 = c * grid_size
            x2 = min((c + 1) * grid_size, w)
            cell = binary[y1:y2, x1:x2]
            grid[r, c] = cell.mean()

    # 활성 셀 찾기
    active = grid > min_density

    # Flood fill로 인접 활성 셀 병합
    visited = np.zeros_like(active, dtype=bool)
    clusters = []

    for r in range(rows):
        for c in range(cols):
            if active[r, c] and not visited[r, c]:
                # BFS flood fill
                cells = []
                queue = [(r, c)]
                visited[r, c] = True
                while queue:
                    cr, cc = queue.pop(0)
                    cells.append((cr, cc))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            if active[nr, nc] and not visited[nr, nc]:
                                visited[nr, nc] = True
                                queue.append((nr, nc))

                # 클러스터 bbox 계산
                min_r = min(cr for cr, cc in cells)
                max_r = max(cr for cr, cc in cells)
                min_c = min(cc for cr, cc in cells)
                max_c = max(cc for cr, cc in cells)

                x1 = min_c * grid_size
                y1 = min_r * grid_size
                x2 = min((max_c + 1) * grid_size, w)
                y2 = min((max_r + 1) * grid_size, h)

                # 밀도 계산
                region = binary[y1:y2, x1:x2]
                density = region.mean()

                # 텍스트 판별: 밀도가 적절한 범위 (너무 높으면 도형, 너무 낮으면 노이즈)
                is_text_like = 0.005 < density < 0.3

                clusters.append({
                    "bbox": (x1, y1, x2, y2),
                    "density": float(density),
                    "is_text_like": is_text_like,
                    "n_cells": len(cells),
                })

    return clusters


# ─────────────────────────────────────────────
# 영역 분류 로직
# ─────────────────────────────────────────────

def classify_regions(
    clusters: list[dict],
    img_w: int,
    img_h: int,
) -> list[dict]:
    """클러스터를 title_block / dimension_area / drawing_body로 분류한다.

    분류 규칙 (MiSUMi/Unit_bearing 도면 패턴):
      - 하단 30% + 텍스트 밀도 → title_block (부품번호 영역)
      - 도형 본체 주변의 작은 텍스트 클러스터 → dimension_area
      - 가장 큰 클러스터 → drawing_body (라벨링 대상 아님)
    """
    if not clusters:
        return []

    labeled = []

    # 면적순 정렬 (큰 것부터)
    sorted_clusters = sorted(clusters, key=lambda c: c["area"], reverse=True)

    # 가장 큰 클러스터 = 도면 본체 (보통 CAD 도형)
    drawing_body = sorted_clusters[0] if sorted_clusters else None
    drawing_body_area = drawing_body["area"] if drawing_body else 0

    for cl in sorted_clusters:
        x1, y1, x2, y2 = cl["bbox"]
        cx = (x1 + x2) / 2 / img_w
        cy = (y1 + y2) / 2 / img_h
        bw = (x2 - x1) / img_w
        bh = (y2 - y1) / img_h
        area_ratio = cl["area"] / (img_w * img_h)

        # 도면 전체의 50% 이상이면 도면 본체 → 스킵
        if area_ratio > 0.5:
            continue

        # title_block 판별: 하단에 위치한 텍스트 영역
        if cy > 0.7 and cl["is_text_like"] and area_ratio < 0.3:
            cl["label"] = "title_block"
            cl["label_id"] = DET_CLASS_MAP["title_block"]
            labeled.append(cl)
            continue

        # dimension_area 판별: 도형 본체 근처의 작은 텍스트
        if cl["is_text_like"] and area_ratio < 0.15 and cl["area"] < drawing_body_area * 0.3:
            # 도면 본체 영역 내부 또는 바로 옆에 있는 텍스트
            if drawing_body:
                db_x1, db_y1, db_x2, db_y2 = drawing_body["bbox"]
                db_cx = (db_x1 + db_x2) / 2 / img_w
                db_cy = (db_y1 + db_y2) / 2 / img_h

                # 도면 본체와 가까운지 확인 (중심 거리)
                dist = ((cx - db_cx) ** 2 + (cy - db_cy) ** 2) ** 0.5
                if dist < 0.5 and cy < 0.7:  # 하단 title 영역 제외
                    cl["label"] = "dimension_area"
                    cl["label_id"] = DET_CLASS_MAP["dimension_area"]
                    labeled.append(cl)

    return labeled


# ─────────────────────────────────────────────
# 라벨 파일 업데이트
# ─────────────────────────────────────────────

def update_label_file(
    label_path: Path,
    regions: list[dict],
    img_w: int,
    img_h: int,
    overwrite: bool = True,
) -> int:
    """YOLO 라벨 파일을 업데이트한다.

    Args:
        label_path: 라벨 파일 경로
        regions: 분류된 영역 리스트
        img_w, img_h: 이미지 크기
        overwrite: True면 기존 라벨 덮어쓰기, False면 추가

    Returns:
        작성된 라벨 수
    """
    lines = []

    if not overwrite and label_path.exists():
        with open(label_path, "r") as f:
            lines = [line.strip() for line in f if line.strip()]

    for region in regions:
        x1, y1, x2, y2 = region["bbox"]
        # YOLO 형식: class_id cx cy w h (정규화)
        cx = ((x1 + x2) / 2) / img_w
        cy = ((y1 + y2) / 2) / img_h
        bw = (x2 - x1) / img_w
        bh = (y2 - y1) / img_h

        # 경계 클램핑
        cx = max(0, min(1, cx))
        cy = max(0, min(1, cy))
        bw = max(0.01, min(1, bw))
        bh = max(0.01, min(1, bh))

        class_id = region["label_id"]
        lines.append(f"{class_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")

    # 중복 제거
    lines = list(dict.fromkeys(lines))

    with open(label_path, "w") as f:
        f.write("\n".join(lines) + "\n" if lines else "")

    return len(lines)


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────

def process_split(
    dataset_dir: Path,
    split: str,
    preview_count: int = 0,
) -> dict:
    """한 split(train/val)의 라벨을 강화한다."""
    img_dir = dataset_dir / "images" / split
    lbl_dir = dataset_dir / "labels" / split

    if not img_dir.exists():
        print(f"  [ERROR] 이미지 디렉토리 없음: {img_dir}")
        return {}

    image_files = sorted([
        f for f in img_dir.iterdir()
        if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".tiff", ".tif"}
    ])

    stats = {
        "total": len(image_files),
        "title_block": 0,
        "dimension_area": 0,
        "parts_table": 0,
        "empty": 0,
        "errors": 0,
    }

    print(f"\n  Processing {split}: {len(image_files):,}장...")

    for idx, img_file in enumerate(image_files):
        try:
            # 이미지 크기
            with Image.open(img_file) as img:
                img_w, img_h = img.size

            # 픽셀 분석
            clusters = analyze_image_regions(img_file)

            # 영역 분류
            regions = classify_regions(clusters, img_w, img_h)

            # 라벨 파일 업데이트
            label_file = lbl_dir / img_file.with_suffix(".txt").name
            n_labels = update_label_file(label_file, regions, img_w, img_h, overwrite=True)

            # 통계
            if n_labels == 0:
                stats["empty"] += 1
            for r in regions:
                label = r.get("label", "")
                if label in stats:
                    stats[label] += 1

            # 프리뷰
            if preview_count > 0 and idx < preview_count:
                print(f"    [{idx+1}] {img_file.name} ({img_w}x{img_h})")
                print(f"        클러스터: {len(clusters)}개, 라벨: {n_labels}개")
                for r in regions:
                    x1, y1, x2, y2 = r["bbox"]
                    print(f"        → {r['label']} ({x1},{y1})-({x2},{y2}) "
                          f"density={r['density']:.3f}")

        except Exception as e:
            stats["errors"] += 1
            if preview_count > 0:
                print(f"    [ERROR] {img_file.name}: {e}")

        # 진행 표시
        if (idx + 1) % 200 == 0:
            print(f"    ... {idx + 1:,}/{len(image_files):,}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="YOLOv8-det 라벨 자동 강화 (픽셀 분석 기반)",
    )
    parser.add_argument(
        "--dataset", type=str, default="./data/det_dataset",
        help="데이터셋 디렉토리 (기본: ./data/det_dataset)",
    )
    parser.add_argument(
        "--split", type=str, default="all",
        choices=["train", "val", "all"],
        help="처리할 split (기본: all)",
    )
    parser.add_argument(
        "--preview", type=int, default=0,
        help="프리뷰 출력할 이미지 수 (기본: 0 = 비활성)",
    )
    parser.add_argument(
        "--bright-threshold", type=int, default=180,
        help="밝은 픽셀 임계값 (기본: 180)",
    )

    args = parser.parse_args()
    dataset_dir = Path(args.dataset)

    print("=" * 65)
    print("  YOLOv8-det 라벨 자동 강화")
    print("=" * 65)

    splits = ["train", "val"] if args.split == "all" else [args.split]
    all_stats = {}

    for split in splits:
        stats = process_split(dataset_dir, split, preview_count=args.preview)
        all_stats[split] = stats

    # 결과 요약
    print(f"\n{'=' * 65}")
    print(f"  강화 완료")
    print(f"{'=' * 65}")
    for split, stats in all_stats.items():
        print(f"\n  [{split}]")
        print(f"    총 이미지: {stats.get('total', 0):,}장")
        print(f"    title_block: {stats.get('title_block', 0):,}개")
        print(f"    dimension_area: {stats.get('dimension_area', 0):,}개")
        print(f"    parts_table: {stats.get('parts_table', 0):,}개")
        print(f"    빈 라벨: {stats.get('empty', 0):,}장")
        print(f"    오류: {stats.get('errors', 0):,}")

    # 통계 저장
    stats_path = dataset_dir / "enhance_stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(all_stats, f, ensure_ascii=False, indent=2)
    print(f"\n  통계 저장: {stats_path}")


if __name__ == "__main__":
    main()
