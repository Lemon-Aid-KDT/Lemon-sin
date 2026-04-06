#!/usr/bin/env python3
"""
YOLOv8-det 도면 영역 탐지 모델 학습 스크립트

사전 학습된 yolov8s.pt를 파인튜닝하여 도면 영역(표제란/치수/부품표) 탐지 모델을 생성한다.

사용법:
  python scripts/train_yolo_det.py --data ./data/det_dataset
  python scripts/train_yolo_det.py --data ./data/det_dataset --epochs 100 --model yolov8m.pt
  python scripts/train_yolo_det.py --data ./data/det_dataset --batch 16 --device mps
  python scripts/train_yolo_det.py --resume runs/detect/train/weights/last.pt

산출물:
  runs/detect/train/weights/best.pt  → 최종 배포 모델
  runs/detect/train/weights/last.pt  → 마지막 에폭 모델
  runs/detect/train/results.csv      → 에폭별 지표
"""

import argparse
import json
import sys
from pathlib import Path


def train(args):
    """YOLOv8-det 탐지 모델을 학습한다."""
    from ultralytics import YOLO

    print("=" * 65)
    print("  YOLOv8-det 영역 탐지 모델 학습")
    print("=" * 65)

    data_dir = Path(args.data)
    yaml_path = data_dir / "dataset.yaml"

    if not yaml_path.exists():
        print(f"  [ERROR] dataset.yaml 없음: {yaml_path}")
        print(f"  → python scripts/prepare_det_dataset.py --output {data_dir}")
        sys.exit(1)

    # 데이터셋 통계 확인
    stats_path = data_dir / "dataset_stats.json"
    if stats_path.exists():
        with open(stats_path, "r", encoding="utf-8") as f:
            stats = json.load(f)
        print(f"\n  데이터셋: {data_dir}")
        print(f"  클래스: {stats.get('num_classes', '?')}개 — {stats.get('classes', [])}")
        print(f"  학습 이미지: {stats.get('train_images', '?'):,}장")
        print(f"  검증 이미지: {stats.get('val_images', '?'):,}장")
    else:
        print(f"\n  데이터셋: {data_dir} (통계 파일 없음)")

    # 라벨 파일 존재 확인
    train_labels_dir = data_dir / "labels" / "train"
    if train_labels_dir.exists():
        non_empty = sum(
            1 for f in train_labels_dir.iterdir()
            if f.suffix == ".txt" and f.stat().st_size > 0
        )
        total_labels = sum(
            1 for f in train_labels_dir.iterdir() if f.suffix == ".txt"
        )
        if non_empty == 0:
            print(f"\n  [WARNING] 라벨 파일이 모두 비어있습니다 ({total_labels}개)")
            print(f"  → 먼저 어노테이션 도구로 bbox 라벨링을 수행하세요.")
            print(f"  → CVAT: python scripts/prepare_det_dataset.py --export-cvat")
            if not args.force:
                print(f"  → --force 옵션으로 강제 학습 가능")
                sys.exit(1)
        else:
            print(f"  라벨: {non_empty}/{total_labels}장 어노테이션 완료")

    # 모델 로드
    if args.resume:
        print(f"\n  학습 재개: {args.resume}")
        model = YOLO(args.resume, task="detect")
    else:
        print(f"\n  베이스 모델: {args.model}")
        model = YOLO(args.model)

    # 학습 파라미터 — 도면 탐지 특화
    train_kwargs = {
        "data": str(yaml_path),
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "patience": args.patience,
        "device": args.device or None,
        "workers": args.workers,
        "project": args.project,
        "name": args.name,
        "exist_ok": True,
        "pretrained": True,
        "optimizer": "auto",
        "cos_lr": True,
        "lr0": args.lr0,
        "seed": args.seed,
        "verbose": True,
        # ── 도면 특화 augmentation ──
        # 도면은 정렬된 상태이며, 표제란 위치가 고정적
        "mosaic": 0.0,        # 모자이크 비활성 (표제란/부품표 위치 파괴 방지)
        "fliplr": 0.0,        # 좌우 반전 비활성 (표제란은 항상 우하단)
        "flipud": 0.0,        # 상하 반전 비활성
        "degrees": 0.0,       # 회전 비활성 (도면은 항상 정렬됨)
        "hsv_h": 0.0,         # 색상 변형 비활성 (흑백 도면)
        "hsv_s": 0.0,         # 채도 변형 비활성
        "hsv_v": 0.2,         # 명도 변형 (스캔 품질 차이 대응)
        "scale": 0.2,         # 스케일 변형 (적당히)
        "translate": 0.1,     # 평행 이동 (적당히)
        "erasing": 0.0,       # Random Erasing 비활성 (bbox 훼손 방지)
    }

    if args.resume:
        train_kwargs["resume"] = True

    print(f"\n  학습 파라미터:")
    for k in ["epochs", "imgsz", "batch", "patience", "lr0", "device"]:
        print(f"    {k}: {train_kwargs.get(k, 'auto')}")
    print(f"    mosaic: 0.0 (비활성)")
    print(f"    fliplr/flipud/degrees: 0.0 (도면 방향 보존)")

    # 학습 실행
    print(f"\n  학습 시작...")
    results = model.train(**train_kwargs)

    # 결과 출력
    print(f"\n{'=' * 65}")
    print(f"  학습 완료")
    print(f"{'=' * 65}")

    weights_dir = Path(args.project) / args.name / "weights"
    best_pt = weights_dir / "best.pt"
    last_pt = weights_dir / "last.pt"

    if best_pt.exists():
        size_mb = best_pt.stat().st_size / (1024 * 1024)
        print(f"  best.pt: {best_pt} ({size_mb:.1f}MB)")
    if last_pt.exists():
        size_mb = last_pt.stat().st_size / (1024 * 1024)
        print(f"  last.pt: {last_pt} ({size_mb:.1f}MB)")

    print(f"\n  다음 단계:")
    print(f"    1. cp {best_pt} models/yolo_det_best.pt")
    print(f"    2. pytest tests/test_detector.py -v")
    print(f"    3. python scripts/evaluate_ocr_accuracy.py")

    return results


def validate(args):
    """학습된 모델의 검증 성능을 평가한다."""
    from ultralytics import YOLO

    print("=" * 65)
    print("  YOLOv8-det 검증 평가")
    print("=" * 65)

    model_path = args.validate
    data_dir = Path(args.data) / "dataset.yaml"

    print(f"\n  모델: {model_path}")
    print(f"  데이터: {data_dir}")

    model = YOLO(model_path, task="detect")
    results = model.val(data=str(data_dir), split="val", verbose=True)

    # Detection 평가 지표
    print(f"\n  mAP@50:    {results.box.map50:.4f}")
    print(f"  mAP@50-95: {results.box.map:.4f}")

    # 클래스별 AP
    if hasattr(results.box, "ap_class_index"):
        names = model.names
        for i, cls_idx in enumerate(results.box.ap_class_index):
            cls_name = names.get(int(cls_idx), f"class_{cls_idx}")
            ap50 = results.box.ap50[i] if i < len(results.box.ap50) else 0
            print(f"    {cls_name}: AP@50={ap50:.4f}")

    return results


def export_model_info(args):
    """모델 메타데이터를 JSON으로 저장한다."""
    from ultralytics import YOLO

    model_path = Path(args.export_info)
    model = YOLO(str(model_path), task="detect")

    info = {
        "model_path": str(model_path),
        "model_name": model_path.name,
        "task": "detect",
        "num_classes": len(model.names),
        "class_names": model.names,
        "input_size": args.imgsz,
        "model_size_mb": round(model_path.stat().st_size / (1024 * 1024), 2),
    }

    output_path = model_path.with_suffix(".json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    print(f"  모델 정보 저장: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="YOLOv8-det 도면 영역 탐지 모델 학습",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # 필수 인자
    parser.add_argument(
        "--data", type=str, default="./data/det_dataset",
        help="학습 데이터셋 디렉토리 (기본: ./data/det_dataset)",
    )

    # 모델 설정
    parser.add_argument(
        "--model", type=str, default="yolov8s.pt",
        help="베이스 모델 (기본: yolov8s.pt — detection 베이스)",
    )
    parser.add_argument(
        "--resume", type=str, default="",
        help="학습 재개할 체크포인트 경로",
    )

    # 학습 파라미터
    parser.add_argument("--epochs", type=int, default=100, help="에폭 수 (기본: 100)")
    parser.add_argument("--imgsz", type=int, default=640, help="입력 이미지 크기 (기본: 640)")
    parser.add_argument("--batch", type=int, default=16, help="배치 크기 (기본: 16)")
    parser.add_argument("--patience", type=int, default=15, help="조기 종료 인내 (기본: 15)")
    parser.add_argument("--lr0", type=float, default=0.01, help="초기 학습률 (기본: 0.01)")
    parser.add_argument("--device", type=str, default="", help="디바이스 (기본: auto)")
    parser.add_argument("--workers", type=int, default=8, help="데이터 로더 워커 수 (기본: 8)")
    parser.add_argument("--seed", type=int, default=42, help="랜덤 시드 (기본: 42)")

    # 출력 경로
    parser.add_argument("--project", type=str, default="runs/detect", help="프로젝트 경로")
    parser.add_argument("--name", type=str, default="train", help="실험 이름")

    # 평가 / 내보내기
    parser.add_argument(
        "--validate", type=str, default="",
        help="모델 검증만 실행 (모델 파일 경로)",
    )
    parser.add_argument(
        "--export-info", type=str, default="",
        help="모델 메타데이터 JSON 내보내기 (모델 파일 경로)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="빈 라벨 경고를 무시하고 강제 학습",
    )

    args = parser.parse_args()

    if args.validate:
        validate(args)
    elif args.export_info:
        export_model_info(args)
    else:
        train(args)


if __name__ == "__main__":
    main()
