"""
CAD Vision — 모델 프리로드 스크립트

Docker 빌드 시 실행되어 ML 모델을 미리 다운로드합니다.
컨테이너 첫 실행 시 모델 다운로드 대기 시간을 없앱니다.
"""

import sys


def preload_clip():
    """OpenCLIP ViT-L-14 모델 다운로드 (~890MB)"""
    print("[1/4] OpenCLIP ViT-L-14 (datacomp_xl_s13b_b90k) 다운로드 중...")
    try:
        import open_clip
        open_clip.create_model_and_transforms(
            "ViT-L-14", pretrained="datacomp_xl_s13b_b90k", device="cpu",
        )
        print("  ✅ OpenCLIP 다운로드 완료")
    except Exception as e:
        print(f"  ⚠️  OpenCLIP 다운로드 실패 (런타임에 재시도): {e}")


def preload_sentence_transformer():
    """SentenceTransformer 모델 다운로드 (~133MB)"""
    print("[2/4] SentenceTransformer (multilingual-e5-small) 다운로드 중...")
    try:
        from sentence_transformers import SentenceTransformer
        SentenceTransformer("intfloat/multilingual-e5-small")
        print("  ✅ SentenceTransformer 다운로드 완료")
    except Exception as e:
        print(f"  ⚠️  SentenceTransformer 다운로드 실패 (런타임에 재시도): {e}")


def preload_paddleocr():
    """PaddleOCR 한국어 모델 다운로드 (~200MB)"""
    print("[3/4] PaddleOCR (Korean) 다운로드 중...")
    try:
        from paddleocr import PaddleOCR
        PaddleOCR(use_textline_orientation=True, lang="korean")
        print("  ✅ PaddleOCR 다운로드 완료")
    except Exception as e:
        print(f"  ⚠️  PaddleOCR 다운로드 실패 (런타임에 재시도): {e}")


def preload_yolo_cls():
    """YOLO-cls 모델 파일 존재 검증"""
    import os
    from pathlib import Path

    print("[4/4] YOLO-cls 모델 검증 중...")
    model_path = os.environ.get("YOLO_CLS_MODEL_PATH", "./models/yolo_cls_best.pt")
    if Path(model_path).exists():
        size_mb = Path(model_path).stat().st_size / (1024 * 1024)
        print(f"  ✅ YOLO-cls 모델 확인: {model_path} ({size_mb:.1f}MB)")
    else:
        print(f"  ⚠️  YOLO-cls 모델 없음: {model_path}")
        print("     → 학습 후 배치하세요: cp runs/classify/train/weights/best.pt models/yolo_cls_best.pt")
        print("     → YOLO 분류기 비활성 상태로 실행됩니다.")


if __name__ == "__main__":
    print("=" * 50)
    print("  CAD Vision — 모델 프리로드")
    print("=" * 50)

    preload_clip()
    preload_sentence_transformer()
    preload_paddleocr()
    preload_yolo_cls()

    print()
    print("✅ 모델 프리로드 완료")
    sys.exit(0)
