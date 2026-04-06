#!/usr/bin/env python3
"""
YOLOv8-cls 73-카테고리 분류 모델 학습 스크립트

사전 학습된 yolov8s-cls.pt를 파인튜닝하여 CAD 도면 분류 모델을 생성한다.

사용법:
  python scripts/train_yolo_cls.py --data ./data/cls_dataset
  python scripts/train_yolo_cls.py --data ./data/cls_dataset --epochs 50 --model yolov8n-cls.pt
  python scripts/train_yolo_cls.py --data ./data/cls_dataset --batch 32 --device mps
  python scripts/train_yolo_cls.py --resume runs/classify/train/weights/last.pt

산출물:
  runs/classify/train/weights/best.pt  → 최종 배포 모델
  runs/classify/train/weights/last.pt  → 마지막 에폭 모델
  runs/classify/train/results.csv      → 에폭별 지표
"""

import argparse
import json
import sys
from pathlib import Path


def train(args):
    """YOLOv8-cls 분류 모델을 학습한다."""
    from ultralytics import YOLO

    print("=" * 65)
    print("  YOLOv8-cls 분류 모델 학습")
    print("=" * 65)

    data_dir = Path(args.data)
    if not data_dir.exists():
        print(f"  [ERROR] 데이터셋 없음: {data_dir}")
        print(f"  → python scripts/prepare_cls_dataset.py --output {data_dir}")
        sys.exit(1)

    # 클래스 수 확인
    train_dir = data_dir / "train"
    if train_dir.exists():
        n_classes = len([d for d in train_dir.iterdir() if d.is_dir()])
        n_images = sum(
            1 for d in train_dir.iterdir() if d.is_dir()
            for f in d.iterdir() if f.suffix.lower() in {".png", ".jpg", ".jpeg"}
        )
        print(f"\n  데이터셋: {data_dir}")
        print(f"  클래스: {n_classes}개")
        print(f"  학습 이미지: {n_images:,}장")
    else:
        print(f"  [ERROR] train 디렉토리 없음: {train_dir}")
        sys.exit(1)

    # 모델 로드
    if args.resume:
        print(f"\n  학습 재개: {args.resume}")
        model = YOLO(args.resume, task="classify")
    else:
        print(f"\n  베이스 모델: {args.model}")
        model = YOLO(args.model)

    # 학습 파라미터
    train_kwargs = {
        "data": str(data_dir),
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
        # 도면 특화 augmentation
        "scale": 0.3,         # 스케일 변형 (적당히)
        "translate": 0.1,     # 평행 이동 (적당히)
        "fliplr": 0.0,        # 좌우 반전 비활성 (도면 방향 중요)
        "flipud": 0.0,        # 상하 반전 비활성
        "hsv_h": 0.0,         # 색상 변형 비활성 (흑백 도면)
        "hsv_s": 0.0,         # 채도 변형 비활성
        "hsv_v": 0.2,         # 명도 변형 (적당히)
        "erasing": 0.1,       # Random Erasing (경미하게)
    }

    if args.resume:
        train_kwargs["resume"] = True

    print(f"\n  학습 파라미터:")
    for k in ["epochs", "imgsz", "batch", "patience", "lr0", "device"]:
        print(f"    {k}: {train_kwargs.get(k, 'auto')}")

    # 학습 실행
    print(f"\n  학습 시작...")
    results = model.train(**train_kwargs)

    # 결과 출력
    print(f"\n{'=' * 65}")
    print(f"  📊 학습 완료")
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
    print(f"    1. cp {best_pt} models/yolo_cls_best.pt")
    print(f"    2. pytest tests/test_classifier.py -v")
    print(f"    3. streamlit run app/streamlit_app.py")

    return results


def validate(args):
    """학습된 모델의 검증 성능을 평가한다."""
    from ultralytics import YOLO

    print("=" * 65)
    print("  YOLOv8-cls 검증 평가")
    print("=" * 65)

    model_path = args.validate
    data_dir = args.data

    print(f"\n  모델: {model_path}")
    print(f"  데이터: {data_dir}")

    model = YOLO(model_path, task="classify")
    results = model.val(data=data_dir, split="val", verbose=True)

    print(f"\n  Top-1 Accuracy: {results.top1:.4f}")
    print(f"  Top-5 Accuracy: {results.top5:.4f}")

    return results


def export_model_info(args):
    """모델 메타데이터를 JSON으로 저장한다."""
    from ultralytics import YOLO

    model_path = Path(args.export_info)
    model = YOLO(str(model_path), task="classify")

    # 클래스명 매핑
    class_names_file = Path(args.data) / "class_names.json"
    class_names = {}
    if class_names_file.exists():
        with open(class_names_file, "r", encoding="utf-8") as f:
            class_names = json.load(f)

    info = {
        "model_path": str(model_path),
        "model_name": model_path.name,
        "task": "classify",
        "num_classes": len(model.names),
        "class_names": model.names,
        "class_names_from_dataset": class_names,
        "input_size": args.imgsz,
        "model_size_mb": round(model_path.stat().st_size / (1024 * 1024), 2),
    }

    output_path = model_path.with_suffix(".json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    print(f"  모델 정보 저장: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="YOLOv8-cls 73-카테고리 분류 모델 학습",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # 필수 인자
    parser.add_argument(
        "--data", type=str, default="./data/cls_dataset",
        help="학습 데이터셋 디렉토리 (기본: ./data/cls_dataset)",
    )

    # 모델 설정
    parser.add_argument(
        "--model", type=str, default="yolov8s-cls.pt",
        help="베이스 모델 (기본: yolov8s-cls.pt)",
    )
    parser.add_argument(
        "--resume", type=str, default="",
        help="학습 재개할 체크포인트 경로",
    )

    # 학습 파라미터
    parser.add_argument("--epochs", type=int, default=50, help="에폭 수 (기본: 50)")
    parser.add_argument("--imgsz", type=int, default=224, help="입력 이미지 크기 (기본: 224)")
    parser.add_argument("--batch", type=int, default=64, help="배치 크기 (기본: 64)")
    parser.add_argument("--patience", type=int, default=10, help="조기 종료 인내 (기본: 10)")
    parser.add_argument("--lr0", type=float, default=0.01, help="초기 학습률 (기본: 0.01)")
    parser.add_argument("--device", type=str, default="", help="디바이스 (기본: auto)")
    parser.add_argument("--workers", type=int, default=8, help="데이터 로더 워커 수 (기본: 8)")
    parser.add_argument("--seed", type=int, default=42, help="랜덤 시드 (기본: 42)")

    # 출력 경로
    parser.add_argument("--project", type=str, default="runs/classify", help="프로젝트 경로")
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

    args = parser.parse_args()

    if args.validate:
        validate(args)
    elif args.export_info:
        export_model_info(args)
    else:
        train(args)


if __name__ == "__main__":
    main()
