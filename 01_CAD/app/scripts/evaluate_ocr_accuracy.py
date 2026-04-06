#!/usr/bin/env python3
"""
OCR 정확도 벤치마크 스크립트

영역 탐지 기반 OCR (Phase 3)의 개선 효과를 정량적으로 측정한다.

비교 대상:
  - Baseline: 전체 이미지 OCR (기존 방식)
  - Enhanced: 영역 탐지 → 크롭 → 영역별 OCR (Phase 3)

측정 지표:
  - 부품번호 Precision / Recall / F1
  - 재질 Precision / Recall / F1
  - 치수 Precision / Recall / F1

사용법:
  python scripts/evaluate_ocr_accuracy.py --ground-truth ./data/ocr_benchmark/ground_truth.json
  python scripts/evaluate_ocr_accuracy.py --ground-truth ./data/ocr_benchmark/ground_truth.json --create-template
  python scripts/evaluate_ocr_accuracy.py --ground-truth ./data/ocr_benchmark/ground_truth.json --det-model ./models/yolo_det_best.pt

Ground Truth JSON 형식:
  {
    "images": [
      {
        "file_path": "/path/to/drawing.png",
        "part_numbers": ["A-1234", "B-5678"],
        "materials": ["SUS304", "S45C"],
        "dimensions": ["M5", "10.5", "45"]
      },
      ...
    ]
  }
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ─────────────────────────────────────────────
# 평가 지표
# ─────────────────────────────────────────────

def _normalize_pn(s: str) -> str:
    """부품번호 정규화 — 리딩 제로 제거 + O↔0 통일 + 대문자화."""
    import re
    s = s.strip().upper()
    # 알파벳 직후의 리딩 제로 제거: ABNZM06 → ABNZM6
    s = re.sub(r"(?<=[A-Z])0+(?=\d)", "", s)
    # O↔0 통일 (OCR 혼동 대응: BTLHO4 → BTLH04)
    s = s.replace("O", "0")
    return s


def _match_part_number(pred: str, gt: str) -> bool:
    """부품번호 퍼지 매칭: 정확 매칭 + 서브스트링 + 리딩제로/O↔0 정규화."""
    p = pred.strip().upper()
    g = gt.strip().upper()

    # 1. 정확 매칭
    if p == g:
        return True

    # 2. 서브스트링 (길이 4+ 조건)
    if len(g) >= 4 and (g in p or p in g):
        return True

    # 3. 리딩제로 + O↔0 정규화 후 매칭
    pn = _normalize_pn(p)
    gn = _normalize_pn(g)
    if pn == gn:
        return True
    if len(gn) >= 4 and (gn in pn or pn in gn):
        return True

    return False


def compute_prf(predicted: list[str], ground_truth: list[str],
                fuzzy: bool = False) -> dict:
    """Precision, Recall, F1을 계산한다.

    대소문자 무시, 공백 제거로 정규화 후 비교.
    fuzzy=True 시 부품번호 퍼지 매칭 (리딩제로/서브스트링) 적용.

    Args:
        predicted: 예측된 항목 리스트
        ground_truth: 정답 항목 리스트
        fuzzy: 부품번호 퍼지 매칭 사용 여부

    Returns:
        {"precision": float, "recall": float, "f1": float,
         "tp": int, "fp": int, "fn": int}
    """
    pred_set = {s.strip().upper() for s in predicted if s.strip()}
    gt_set = {s.strip().upper() for s in ground_truth if s.strip()}

    if not gt_set and not pred_set:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0,
                "tp": 0, "fp": 0, "fn": 0}

    if fuzzy:
        # 퍼지 매칭: GT 각 항목에 대해 최적 pred 매칭
        matched_pred: set[str] = set()
        matched_gt: set[str] = set()
        for g in gt_set:
            for p in pred_set:
                if p in matched_pred:
                    continue
                if _match_part_number(p, g):
                    matched_pred.add(p)
                    matched_gt.add(g)
                    break
        tp = len(matched_gt)
        fp = len(pred_set) - len(matched_pred)
        fn = len(gt_set) - len(matched_gt)
    else:
        tp = len(pred_set & gt_set)
        fp = len(pred_set - gt_set)
        fn = len(gt_set - pred_set)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {"precision": precision, "recall": recall, "f1": f1,
            "tp": tp, "fp": fp, "fn": fn}


def aggregate_metrics(metrics_list: list[dict]) -> dict:
    """여러 이미지의 지표를 매크로 평균으로 집계한다."""
    if not metrics_list:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    n = len(metrics_list)
    avg_p = sum(m["precision"] for m in metrics_list) / n
    avg_r = sum(m["recall"] for m in metrics_list) / n
    avg_f1 = sum(m["f1"] for m in metrics_list) / n
    total_tp = sum(m["tp"] for m in metrics_list)
    total_fp = sum(m["fp"] for m in metrics_list)
    total_fn = sum(m["fn"] for m in metrics_list)

    return {
        "macro_precision": round(avg_p, 4),
        "macro_recall": round(avg_r, 4),
        "macro_f1": round(avg_f1, 4),
        "total_tp": total_tp,
        "total_fp": total_fp,
        "total_fn": total_fn,
    }


# ─────────────────────────────────────────────
# Baseline OCR (전체 이미지)
# ─────────────────────────────────────────────

def run_baseline_ocr(image_path: str, ocr_engine) -> dict:
    """전체 이미지에 OCR을 실행하여 추출 결과를 반환한다.

    Returns:
        {"part_numbers": [...], "materials": [...], "dimensions": [...]}
    """
    try:
        result = ocr_engine.extract(image_path)
        return {
            "part_numbers": result.part_numbers,
            "materials": result.materials,
            "dimensions": result.dimensions,
        }
    except Exception as e:
        print(f"    [ERROR] Baseline OCR 실패 ({image_path}): {e}")
        return {"part_numbers": [], "materials": [], "dimensions": []}


# ─────────────────────────────────────────────
# Enhanced OCR (영역 탐지 기반)
# ─────────────────────────────────────────────

def run_enhanced_ocr(image_path: str, ocr_engine, detector) -> dict:
    """영역 탐지 → 크롭 → 영역별 OCR → 병합 결과를 반환한다.

    Returns:
        {"part_numbers": [...], "materials": [...], "dimensions": [...],
         "regions_detected": int}
    """
    try:
        # 기본 OCR (전체 이미지)
        base_result = ocr_engine.extract(image_path)

        # 영역 탐지
        det_result = detector.detect(image_path)

        if not det_result.regions:
            return {
                "part_numbers": base_result.part_numbers,
                "materials": base_result.materials,
                "dimensions": base_result.dimensions,
                "regions_detected": 0,
            }

        # 영역별 OCR
        region_ocr_results = []
        for region in det_result.regions:
            try:
                cropped = detector.crop_region(image_path, region)
                region_ocr = ocr_engine.extract_region(cropped, region.class_name)
                region_ocr.bbox = region.bbox
                region_ocr_results.append(region_ocr)
            except Exception:
                pass

        # 결과 병합 (pipeline._merge_ocr_results 로직)
        merged_parts = list(base_result.part_numbers)
        merged_materials = list(base_result.materials)
        merged_dims = list(base_result.dimensions)

        for r_ocr in region_ocr_results:
            sd = r_ocr.structured_data
            if r_ocr.region_class == "title_block":
                pn = sd.get("drawing_number", "")
                if pn:
                    # 퍼지 중복 체크: 기존 부품번호와 서브스트링/정규화 비교
                    already_exists = any(
                        _match_part_number(pn, ep) for ep in merged_parts
                    )
                    if not already_exists:
                        merged_parts.insert(0, pn)
                mat = sd.get("material", "")
                if mat and mat not in merged_materials:
                    merged_materials.insert(0, mat)
            elif r_ocr.region_class == "dimension_area":
                for dim in sd.get("dimensions", []):
                    if dim not in merged_dims:
                        merged_dims.append(dim)

        return {
            "part_numbers": merged_parts,
            "materials": merged_materials,
            "dimensions": merged_dims,
            "regions_detected": len(det_result.regions),
        }

    except Exception as e:
        print(f"    [ERROR] Enhanced OCR 실패 ({image_path}): {e}")
        return {"part_numbers": [], "materials": [], "dimensions": [],
                "regions_detected": 0}


# ─────────────────────────────────────────────
# 템플릿 생성
# ─────────────────────────────────────────────

def create_ground_truth_template(output_path: Path) -> None:
    """Ground truth JSON 템플릿을 생성한다."""
    template = {
        "_description": "OCR 정확도 벤치마크 Ground Truth",
        "_instructions": [
            "images 배열에 벤치마크 도면을 추가하세요.",
            "part_numbers: 도면에 있는 모든 부품번호 (도번, 품번 포함)",
            "materials: 도면에 기재된 재질 (SUS304, S45C, AL6061 등)",
            "dimensions: 주요 치수 값 (단위 제외, 문자열로)",
        ],
        "images": [
            {
                "file_path": "/path/to/drawing1.png",
                "part_numbers": ["A-1234", "B-5678"],
                "materials": ["SUS304"],
                "dimensions": ["10.5", "M5", "45"],
            },
            {
                "file_path": "/path/to/drawing2.png",
                "part_numbers": ["C-9012"],
                "materials": ["S45C", "AL6061"],
                "dimensions": ["25", "50", "R10"],
            },
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)
    print(f"  Ground Truth 템플릿 생성: {output_path}")
    print(f"  → 실제 도면 경로와 정답 데이터로 수정하세요.")


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="OCR 정확도 벤치마크 (Baseline vs Enhanced)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--ground-truth", type=str,
        default="./data/ocr_benchmark/ground_truth.json",
        help="Ground Truth JSON 경로 (기본: ./data/ocr_benchmark/ground_truth.json)",
    )
    parser.add_argument(
        "--det-model", type=str, default="./models/yolo_det_best.pt",
        help="YOLOv8-det 모델 경로 (기본: ./models/yolo_det_best.pt)",
    )
    parser.add_argument(
        "--det-confidence", type=float, default=0.3,
        help="탐지 신뢰도 임계값 (기본: 0.3)",
    )
    parser.add_argument(
        "--ocr-lang", type=str, default="korean",
        help="OCR 언어 (기본: korean)",
    )
    parser.add_argument(
        "--create-template", action="store_true",
        help="Ground Truth 템플릿 JSON 생성",
    )
    parser.add_argument(
        "--output", type=str, default="",
        help="결과 JSON 저장 경로 (미지정 시 stdout만 출력)",
    )
    parser.add_argument(
        "--baseline-only", action="store_true",
        help="Baseline OCR만 평가 (탐지기 없이)",
    )

    args = parser.parse_args()

    print("=" * 65)
    print("  OCR 정확도 벤치마크")
    print("=" * 65)

    # 템플릿 생성 모드
    if args.create_template:
        create_ground_truth_template(Path(args.ground_truth))
        return

    # Ground Truth 로드
    gt_path = Path(args.ground_truth)
    if not gt_path.exists():
        print(f"  [ERROR] Ground Truth 파일 없음: {gt_path}")
        print(f"  → --create-template 으로 템플릿을 먼저 생성하세요.")
        sys.exit(1)

    with open(gt_path, "r", encoding="utf-8") as f:
        gt_data = json.load(f)

    images = gt_data.get("images", [])
    if not images:
        print("  [ERROR] Ground Truth에 이미지가 없습니다.")
        sys.exit(1)

    # 존재하는 이미지만 필터
    valid_images = []
    for img in images:
        if Path(img["file_path"]).exists():
            valid_images.append(img)
        else:
            print(f"  [WARNING] 이미지 없음 (건너뜀): {img['file_path']}")

    if not valid_images:
        print("  [ERROR] 유효한 이미지가 없습니다.")
        sys.exit(1)

    print(f"\n  벤치마크 이미지: {len(valid_images)}장")

    # OCR 엔진 초기화
    from core.ocr import DrawingOCR
    print(f"  OCR 엔진 초기화 (lang={args.ocr_lang})...")
    ocr_engine = DrawingOCR(lang=args.ocr_lang)

    # ── Baseline 평가 ──
    print(f"\n{'─' * 65}")
    print(f"  [1/2] Baseline OCR (전체 이미지)")
    print(f"{'─' * 65}")

    baseline_pn_metrics = []
    baseline_mat_metrics = []
    baseline_dim_metrics = []

    start_time = time.time()
    for i, img_data in enumerate(valid_images):
        fpath = img_data["file_path"]
        result = run_baseline_ocr(fpath, ocr_engine)

        pn_m = compute_prf(result["part_numbers"], img_data.get("part_numbers", []), fuzzy=True)
        mat_m = compute_prf(result["materials"], img_data.get("materials", []))
        dim_m = compute_prf(result["dimensions"], img_data.get("dimensions", []))

        baseline_pn_metrics.append(pn_m)
        baseline_mat_metrics.append(mat_m)
        baseline_dim_metrics.append(dim_m)

        print(f"    [{i+1}/{len(valid_images)}] {Path(fpath).name} "
              f"— PN F1={pn_m['f1']:.2f}, MAT F1={mat_m['f1']:.2f}, "
              f"DIM F1={dim_m['f1']:.2f}")

    baseline_time = time.time() - start_time

    baseline_results = {
        "part_numbers": aggregate_metrics(baseline_pn_metrics),
        "materials": aggregate_metrics(baseline_mat_metrics),
        "dimensions": aggregate_metrics(baseline_dim_metrics),
        "time_seconds": round(baseline_time, 1),
    }

    print(f"\n  Baseline 결과:")
    for field_name, metrics in [
        ("부품번호", baseline_results["part_numbers"]),
        ("재질", baseline_results["materials"]),
        ("치수", baseline_results["dimensions"]),
    ]:
        print(f"    {field_name}: P={metrics['macro_precision']:.4f} "
              f"R={metrics['macro_recall']:.4f} F1={metrics['macro_f1']:.4f}")
    print(f"    소요 시간: {baseline_time:.1f}초")

    # ── Enhanced 평가 ──
    enhanced_results = None
    if not args.baseline_only:
        det_model_path = Path(args.det_model)
        if not det_model_path.exists():
            print(f"\n  [WARNING] 탐지 모델 없음: {det_model_path}")
            print(f"  → Enhanced OCR 평가를 건너뜁니다.")
        else:
            from core.detector import DrawingDetector

            print(f"\n{'─' * 65}")
            print(f"  [2/2] Enhanced OCR (영역 탐지 기반)")
            print(f"{'─' * 65}")

            detector = DrawingDetector(
                model_path=args.det_model,
                confidence_threshold=args.det_confidence,
            )

            enhanced_pn_metrics = []
            enhanced_mat_metrics = []
            enhanced_dim_metrics = []
            total_regions = 0

            start_time = time.time()
            for i, img_data in enumerate(valid_images):
                fpath = img_data["file_path"]
                result = run_enhanced_ocr(fpath, ocr_engine, detector)

                pn_m = compute_prf(result["part_numbers"], img_data.get("part_numbers", []), fuzzy=True)
                mat_m = compute_prf(result["materials"], img_data.get("materials", []))
                dim_m = compute_prf(result["dimensions"], img_data.get("dimensions", []))

                enhanced_pn_metrics.append(pn_m)
                enhanced_mat_metrics.append(mat_m)
                enhanced_dim_metrics.append(dim_m)
                total_regions += result.get("regions_detected", 0)

                print(f"    [{i+1}/{len(valid_images)}] {Path(fpath).name} "
                      f"— PN F1={pn_m['f1']:.2f}, MAT F1={mat_m['f1']:.2f}, "
                      f"DIM F1={dim_m['f1']:.2f} ({result.get('regions_detected', 0)} regions)")

            enhanced_time = time.time() - start_time

            enhanced_results = {
                "part_numbers": aggregate_metrics(enhanced_pn_metrics),
                "materials": aggregate_metrics(enhanced_mat_metrics),
                "dimensions": aggregate_metrics(enhanced_dim_metrics),
                "time_seconds": round(enhanced_time, 1),
                "total_regions_detected": total_regions,
            }

            print(f"\n  Enhanced 결과:")
            for field_name, metrics in [
                ("부품번호", enhanced_results["part_numbers"]),
                ("재질", enhanced_results["materials"]),
                ("치수", enhanced_results["dimensions"]),
            ]:
                print(f"    {field_name}: P={metrics['macro_precision']:.4f} "
                      f"R={metrics['macro_recall']:.4f} F1={metrics['macro_f1']:.4f}")
            print(f"    소요 시간: {enhanced_time:.1f}초")
            print(f"    탐지 영역: {total_regions}개 (평균 {total_regions / len(valid_images):.1f}개/장)")

    # ── 비교 ──
    print(f"\n{'=' * 65}")
    print(f"  벤치마크 비교")
    print(f"{'=' * 65}")

    if enhanced_results:
        for field_name, bl_key in [
            ("부품번호", "part_numbers"),
            ("재질", "materials"),
            ("치수", "dimensions"),
        ]:
            bl_f1 = baseline_results[bl_key]["macro_f1"]
            en_f1 = enhanced_results[bl_key]["macro_f1"]
            delta = en_f1 - bl_f1
            pct = (delta / bl_f1 * 100) if bl_f1 > 0 else float("inf")
            arrow = "+" if delta >= 0 else ""
            print(f"  {field_name}:")
            print(f"    Baseline F1: {bl_f1:.4f}")
            print(f"    Enhanced F1: {en_f1:.4f}")
            print(f"    변화: {arrow}{delta:.4f} ({arrow}{pct:.1f}%)")

        # 종합 F1
        bl_avg_f1 = (
            baseline_results["part_numbers"]["macro_f1"]
            + baseline_results["materials"]["macro_f1"]
            + baseline_results["dimensions"]["macro_f1"]
        ) / 3
        en_avg_f1 = (
            enhanced_results["part_numbers"]["macro_f1"]
            + enhanced_results["materials"]["macro_f1"]
            + enhanced_results["dimensions"]["macro_f1"]
        ) / 3
        overall_delta = en_avg_f1 - bl_avg_f1
        overall_pct = (overall_delta / bl_avg_f1 * 100) if bl_avg_f1 > 0 else 0

        print(f"\n  종합 F1 (3필드 평균):")
        print(f"    Baseline: {bl_avg_f1:.4f}")
        print(f"    Enhanced: {en_avg_f1:.4f}")
        arrow = "+" if overall_pct >= 0 else ""
        print(f"    개선율: {arrow}{overall_pct:.1f}%")

        if overall_pct >= 20:
            print(f"\n  목표 달성: OCR 정확도 +20% 이상 개선!")
        elif overall_pct >= 10:
            print(f"\n  부분 개선: +10% 이상. 추가 어노테이션/모델 튜닝 필요.")
        else:
            print(f"\n  개선 부족: 어노테이션 품질/탐지 모델 성능 확인 필요.")
    else:
        print(f"  Enhanced OCR 미실행 (탐지 모델 필요)")
        print(f"  Baseline F1:")
        for field_name, bl_key in [
            ("부품번호", "part_numbers"),
            ("재질", "materials"),
            ("치수", "dimensions"),
        ]:
            bl_f1 = baseline_results[bl_key]["macro_f1"]
            print(f"    {field_name}: {bl_f1:.4f}")

    # ── 결과 저장 ──
    if args.output:
        output_data = {
            "benchmark_images": len(valid_images),
            "baseline": baseline_results,
        }
        if enhanced_results:
            output_data["enhanced"] = enhanced_results
            output_data["improvement"] = {
                "part_numbers_f1_delta": round(
                    enhanced_results["part_numbers"]["macro_f1"]
                    - baseline_results["part_numbers"]["macro_f1"], 4
                ),
                "materials_f1_delta": round(
                    enhanced_results["materials"]["macro_f1"]
                    - baseline_results["materials"]["macro_f1"], 4
                ),
                "dimensions_f1_delta": round(
                    enhanced_results["dimensions"]["macro_f1"]
                    - baseline_results["dimensions"]["macro_f1"], 4
                ),
            }

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n  결과 저장: {output_path}")


if __name__ == "__main__":
    main()
