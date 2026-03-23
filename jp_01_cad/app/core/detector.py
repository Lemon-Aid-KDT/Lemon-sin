"""
YOLO-det 기반 도면 영역 탐지 모듈

도면 이미지에서 표제란(title_block), 치수 영역(dimension_area), 부품표(parts_table)를
자동 탐지하여 영역별 OCR 파이프라인의 기반을 제공한다.

주요 클래스:
  - DetectedRegion: 단일 탐지 영역 데이터
  - DetectionResult: 전체 탐지 결과
  - DrawingDetector: YOLO-det 추론 래퍼
"""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from loguru import logger
from PIL import Image


@dataclass
class DetectedRegion:
    """단일 탐지 영역"""

    class_name: str = ""            # "title_block" | "dimension_area" | "parts_table"
    confidence: float = 0.0         # 탐지 신뢰도 (0.0~1.0)
    bbox: tuple[int, int, int, int] = (0, 0, 0, 0)  # (x1, y1, x2, y2) 픽셀 좌표
    bbox_normalized: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)  # 0~1 정규화


@dataclass
class DetectionResult:
    """전체 탐지 결과"""

    regions: list[DetectedRegion] = field(default_factory=list)
    image_size: tuple[int, int] = (0, 0)  # (width, height)
    model_name: str = ""

    def get_regions_by_class(self, class_name: str) -> list[DetectedRegion]:
        """특정 클래스의 영역만 필터링"""
        return [r for r in self.regions if r.class_name == class_name]

    @property
    def title_blocks(self) -> list[DetectedRegion]:
        """표제란 영역 목록"""
        return self.get_regions_by_class("title_block")

    @property
    def dimension_areas(self) -> list[DetectedRegion]:
        """치수 영역 목록"""
        return self.get_regions_by_class("dimension_area")

    @property
    def parts_tables(self) -> list[DetectedRegion]:
        """부품표 영역 목록"""
        return self.get_regions_by_class("parts_table")


class DrawingDetector:
    """YOLO-det 기반 도면 영역 탐지기

    DrawingClassifier와 동일한 지연 로딩 패턴을 따른다:
      - __init__에서 설정만 저장
      - 첫 번째 detect() 호출 시 _init_model() 실행
      - GPU OOM 시 CPU 폴백

    사용법:
        detector = DrawingDetector("models/yolo_det_best.pt")
        result = detector.detect("path/to/drawing.png")
        for region in result.title_blocks:
            print(region.class_name, region.confidence, region.bbox)
    """

    def __init__(
        self,
        model_path: str | Path = "./models/yolo_det_best.pt",
        confidence_threshold: float = 0.3,
        iou_threshold: float = 0.5,
        device: str = "",
        expected_sha256: str = "",
    ):
        """
        Args:
            model_path: YOLO-det 학습 완료 모델 (.pt) 경로
            confidence_threshold: 이 값 미만의 탐지 결과는 제외
            iou_threshold: NMS(Non-Maximum Suppression) IoU 임계값
            device: 연산 디바이스 ("", "cpu", "cuda", "mps"). 빈 문자열이면 자동 선택.
            expected_sha256: 모델 파일의 기대 SHA256 해시 (빈 문자열이면 검증 스킵)
        """
        self.model_path = Path(model_path)
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self._device = device
        self._expected_sha256 = expected_sha256
        self._model = None

    # ─────────────────────────────────────────────
    # 모델 초기화
    # ─────────────────────────────────────────────

    @staticmethod
    def compute_file_sha256(file_path: Path) -> str:
        """파일의 SHA256 해시를 계산한다."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _verify_model_checksum(self):
        """모델 파일의 SHA256 체크섬을 검증한다 (pickle 역직렬화 전 안전 확인).

        Raises:
            ValueError: 체크섬 불일치 시
        """
        if not self._expected_sha256:
            logger.debug("모델 SHA256 체크섬 미설정 → 검증 스킵")
            return

        actual = self.compute_file_sha256(self.model_path)
        if actual != self._expected_sha256.lower():
            raise ValueError(
                f"모델 파일 무결성 검증 실패!\n"
                f"  경로: {self.model_path}\n"
                f"  기대 SHA256: {self._expected_sha256}\n"
                f"  실제 SHA256: {actual}\n"
                f"  → 모델 파일이 변조되었을 수 있습니다. 원본 파일로 교체하세요."
            )
        logger.info(f"모델 SHA256 체크섬 검증 통과: {actual[:16]}...")

    def _init_model(self):
        """YOLO-det 모델 지연 로딩

        ultralytics는 detect() 최초 호출 시점에만 import/로딩된다.
        GPU OOM 발생 시 CPU로 자동 폴백한다.
        """
        if self._model is not None:
            return

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"YOLO-det 모델 파일 없음: {self.model_path}\n"
                f"  → python scripts/train_yolo_det.py --data ./data/det_dataset\n"
                f"  → cp runs/detect/train/weights/best.pt {self.model_path}"
            )

        # pickle 역직렬화 전 체크섬 검증
        self._verify_model_checksum()

        try:
            from ultralytics import YOLO

            logger.info(f"YOLO-det 모델 로딩: {self.model_path}")
            self._model = YOLO(str(self.model_path), task="detect")

            if self._device:
                logger.info(f"YOLO-det 디바이스: {self._device}")

            logger.info(
                f"YOLO-det 모델 로딩 완료 "
                f"(클래스: {len(self._model.names)}개)"
            )
        except ImportError:
            raise RuntimeError(
                "ultralytics 미설치: pip install ultralytics>=8.4.0"
            )
        except RuntimeError as e:
            if "out of memory" in str(e).lower() or "CUDA" in str(e):
                logger.error(
                    f"GPU 메모리 부족으로 YOLO-det 로딩 실패, CPU로 재시도: {e}"
                )
                from ultralytics import YOLO

                self._device = "cpu"
                self._model = YOLO(str(self.model_path), task="detect")
                logger.info("YOLO-det 모델 CPU 로딩 완료 (GPU 메모리 부족)")
            else:
                raise RuntimeError(f"YOLO-det 모델 로딩 실패: {e}") from e

    # ─────────────────────────────────────────────
    # 탐지 추론
    # ─────────────────────────────────────────────

    def detect(self, image_path: str | Path) -> DetectionResult:
        """
        단일 도면 이미지에서 영역을 탐지한다.

        Args:
            image_path: 도면 이미지 파일 경로

        Returns:
            DetectionResult: 탐지된 영역 목록

        Raises:
            FileNotFoundError: 이미지 파일이 없을 때
            RuntimeError: 모델 로딩 실패 시
        """
        self._init_model()

        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"이미지 파일 없음: {image_path}")

        try:
            # Note: YOLO26 end-to-end 모델은 NMS가 내장되어 있어 'iou' 파라미터가
            # 무시될 수 있음. YOLOv8 모델이나 YOLO26 end2end=False 모드에서만 유효.
            # 출력 형식(result.boxes.*)은 ultralytics가 통일하므로 호환성 문제 없음.
            predict_kwargs = {
                "source": str(image_path),
                "verbose": False,
                "conf": self.confidence_threshold,
                "iou": self.iou_threshold,
            }
            if self._device:
                predict_kwargs["device"] = self._device

            results = self._model.predict(**predict_kwargs)

            if not results or len(results) == 0:
                logger.warning(f"YOLO-det 결과 없음: {image_path.name}")
                return DetectionResult(model_name=self.model_path.name)

            result = results[0]
            boxes = result.boxes

            # 이미지 크기 (height, width) → (width, height)
            orig_h, orig_w = result.orig_shape
            image_size = (orig_w, orig_h)

            regions = []
            if boxes is not None and len(boxes) > 0:
                xyxy_arr = boxes.xyxy.cpu().numpy()
                conf_arr = boxes.conf.cpu().numpy()
                cls_arr = boxes.cls.cpu().numpy().astype(int)

                for xyxy, conf, cls_idx in zip(xyxy_arr, conf_arr, cls_arr):
                    x1, y1, x2, y2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])
                    class_name = self._model.names.get(cls_idx, f"class_{cls_idx}")

                    # 정규화 좌표
                    bbox_norm = (
                        round(x1 / orig_w, 4),
                        round(y1 / orig_h, 4),
                        round(x2 / orig_w, 4),
                        round(y2 / orig_h, 4),
                    )

                    regions.append(DetectedRegion(
                        class_name=class_name,
                        confidence=round(float(conf), 4),
                        bbox=(x1, y1, x2, y2),
                        bbox_normalized=bbox_norm,
                    ))

            logger.info(
                f"YOLO-det 탐지 완료: {image_path.name} "
                f"({len(regions)}개 영역)"
            )

            return DetectionResult(
                regions=regions,
                image_size=image_size,
                model_name=self.model_path.name,
            )

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"YOLO-det 추론 실패 ({image_path.name}): {e}")
            return DetectionResult(model_name=self.model_path.name)

    def detect_batch(
        self,
        image_paths: list[str | Path],
        batch_size: int = 16,
    ) -> list[DetectionResult]:
        """
        여러 도면 이미지를 배치로 탐지한다.

        Args:
            image_paths: 이미지 파일 경로 리스트
            batch_size: 배치 크기

        Returns:
            list[DetectionResult]: 입력 순서에 대응하는 탐지 결과 리스트
        """
        self._init_model()

        all_results = []
        total = len(image_paths)

        for i in range(0, total, batch_size):
            batch_paths = image_paths[i:i + batch_size]
            batch_str = [str(p) for p in batch_paths]

            try:
                predict_kwargs = {
                    "source": batch_str,
                    "verbose": False,
                    "conf": self.confidence_threshold,
                    "iou": self.iou_threshold,
                }
                if self._device:
                    predict_kwargs["device"] = self._device

                results = self._model.predict(**predict_kwargs)

                for result in results:
                    boxes = result.boxes
                    orig_h, orig_w = result.orig_shape
                    image_size = (orig_w, orig_h)

                    regions = []
                    if boxes is not None and len(boxes) > 0:
                        xyxy_arr = boxes.xyxy.cpu().numpy()
                        conf_arr = boxes.conf.cpu().numpy()
                        cls_arr = boxes.cls.cpu().numpy().astype(int)

                        for xyxy, conf, cls_idx in zip(xyxy_arr, conf_arr, cls_arr):
                            x1, y1, x2, y2 = (
                                int(xyxy[0]), int(xyxy[1]),
                                int(xyxy[2]), int(xyxy[3]),
                            )
                            class_name = self._model.names.get(
                                cls_idx, f"class_{cls_idx}"
                            )
                            bbox_norm = (
                                round(x1 / orig_w, 4),
                                round(y1 / orig_h, 4),
                                round(x2 / orig_w, 4),
                                round(y2 / orig_h, 4),
                            )
                            regions.append(DetectedRegion(
                                class_name=class_name,
                                confidence=round(float(conf), 4),
                                bbox=(x1, y1, x2, y2),
                                bbox_normalized=bbox_norm,
                            ))

                    all_results.append(DetectionResult(
                        regions=regions,
                        image_size=image_size,
                        model_name=self.model_path.name,
                    ))

                logger.debug(
                    f"배치 탐지 완료: {min(i + batch_size, total)}/{total}"
                )

            except Exception as e:
                logger.error(
                    f"배치 탐지 실패 (batch {i}~{i + len(batch_paths)}): {e}"
                )
                # 실패한 배치는 개별 처리로 폴백
                for path in batch_paths:
                    try:
                        all_results.append(self.detect(path))
                    except Exception as inner_e:
                        logger.error(f"개별 탐지도 실패 ({path}): {inner_e}")
                        all_results.append(DetectionResult(
                            model_name=self.model_path.name,
                        ))

        return all_results

    # ─────────────────────────────────────────────
    # 영역 크롭
    # ─────────────────────────────────────────────

    def crop_region(
        self,
        image_path: str | Path,
        region: DetectedRegion,
        padding: int = 10,
    ) -> Image.Image:
        """
        탐지된 영역을 이미지에서 크롭한다.

        OCR 정확도를 위해 영역 외곽에 padding을 추가한다.

        Args:
            image_path: 원본 이미지 경로
            region: 탐지된 영역 정보
            padding: 크롭 외곽 여백 (픽셀)

        Returns:
            PIL.Image: 크롭된 영역 이미지
        """
        img = Image.open(image_path)
        w, h = img.size

        x1, y1, x2, y2 = region.bbox

        # 경계 클램핑 + 패딩
        crop_x1 = max(0, x1 - padding)
        crop_y1 = max(0, y1 - padding)
        crop_x2 = min(w, x2 + padding)
        crop_y2 = min(h, y2 + padding)

        cropped = img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
        return cropped

    # ─────────────────────────────────────────────
    # 속성 / 유틸리티
    # ─────────────────────────────────────────────

    @property
    def class_names(self) -> list[str]:
        """모델이 학습한 클래스명 목록"""
        self._init_model()
        return list(self._model.names.values())

    @property
    def num_classes(self) -> int:
        """모델 클래스 수"""
        self._init_model()
        return len(self._model.names)

    def check_health(self) -> tuple[bool, str]:
        """모델 상태 확인

        Returns:
            (healthy, message): 모델 사용 가능 여부와 상세 메시지
        """
        if not self.model_path.exists():
            return False, f"모델 파일 없음: {self.model_path}"

        try:
            self._init_model()
            n = len(self._model.names)
            return True, f"YOLO-det 정상 ({n}클래스, {self.model_path.name})"
        except Exception as e:
            return False, f"YOLO-det 로딩 실패: {e}"
