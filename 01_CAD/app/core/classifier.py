"""
YOLO-cls 기반 도면 자동분류 모듈

사전 학습된 YOLO-cls 모델로 73카테고리 CAD 도면을 ~50ms 내 분류한다.
Ollama LLM 분류(5~30초)를 대체하여 등록/대시보드/검색 시 고속 분류를 제공한다.

주요 클래스:
  - ClassificationResult: 분류 결과 데이터
  - DrawingClassifier: YOLO-cls 추론 래퍼
"""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger


@dataclass
class ClassificationResult:
    """YOLO-cls 분류 결과"""

    category: str = ""                              # 최상위 예측 카테고리
    confidence: float = 0.0                         # 최상위 예측 신뢰도 (0.0~1.0)
    top_k: list[tuple[str, float]] = field(         # Top-K 후보 [(카테고리, 신뢰도), ...]
        default_factory=list,
    )
    needs_review: bool = False                      # 신뢰도 < threshold → 수동 검토 권장
    model_name: str = ""                            # 사용된 모델 파일명


class DrawingClassifier:
    """YOLO-cls 기반 도면 분류기

    기존 ImageEmbedder와 동일한 지연 로딩 패턴을 따른다:
      - __init__에서 설정만 저장
      - 첫 번째 classify() 호출 시 _init_model() 실행
      - GPU OOM 시 CPU 폴백

    사용법:
        classifier = DrawingClassifier("models/yolo_cls_best.pt")
        result = classifier.classify("path/to/drawing.png")
        print(result.category, result.confidence)
    """

    def __init__(
        self,
        model_path: str | Path = "./models/yolo_cls_best.pt",
        confidence_threshold: float = 0.5,
        device: str = "",
        expected_sha256: str = "",
    ):
        """
        Args:
            model_path: YOLO-cls 학습 완료 모델 (.pt) 경로
            confidence_threshold: 이 값 미만이면 needs_review=True
            device: 연산 디바이스 ("", "cpu", "cuda", "mps"). 빈 문자열이면 자동 선택.
            expected_sha256: 모델 파일의 기대 SHA256 해시 (빈 문자열이면 검증 스킵)
        """
        self.model_path = Path(model_path)
        self.confidence_threshold = confidence_threshold
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

        .pt 파일은 pickle 기반이므로 악의적으로 변조된 모델은
        임의 코드를 실행할 수 있다. 체크섬 검증으로 무결성을 보장한다.

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
        """YOLO-cls 모델 지연 로딩

        ultralytics는 classify() 최초 호출 시점에만 import/로딩된다.
        GPU OOM 발생 시 CPU로 자동 폴백한다.
        """
        if self._model is not None:
            return

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"YOLO-cls 모델 파일 없음: {self.model_path}\n"
                f"  → python scripts/train_yolo_cls.py --data ./data/cls_dataset\n"
                f"  → cp runs/classify/train/weights/best.pt {self.model_path}"
            )

        # pickle 역직렬화 전 체크섬 검증
        self._verify_model_checksum()

        try:
            from ultralytics import YOLO

            logger.info(f"YOLO-cls 모델 로딩: {self.model_path}")
            self._model = YOLO(str(self.model_path), task="classify")

            # 디바이스 설정 (빈 문자열이면 ultralytics 자동 선택)
            if self._device:
                logger.info(f"YOLO-cls 디바이스: {self._device}")

            logger.info(
                f"YOLO-cls 모델 로딩 완료 "
                f"(클래스: {len(self._model.names)}개)"
            )
        except ImportError:
            raise RuntimeError(
                "ultralytics 미설치: pip install ultralytics>=8.4.0"
            )
        except RuntimeError as e:
            if "out of memory" in str(e).lower() or "CUDA" in str(e):
                logger.error(f"GPU 메모리 부족으로 YOLO-cls 로딩 실패, CPU로 재시도: {e}")
                from ultralytics import YOLO

                self._device = "cpu"
                self._model = YOLO(str(self.model_path), task="classify")
                logger.info("YOLO-cls 모델 CPU 로딩 완료 (GPU 메모리 부족)")
            else:
                raise RuntimeError(f"YOLO-cls 모델 로딩 실패: {e}") from e

    # ─────────────────────────────────────────────
    # 분류 추론
    # ─────────────────────────────────────────────

    def classify(
        self,
        image_path: str | Path,
        top_k: int = 5,
    ) -> ClassificationResult:
        """
        단일 도면 이미지를 분류한다.

        Args:
            image_path: 도면 이미지 파일 경로
            top_k: 상위 K개 후보 반환 (기본: 5)

        Returns:
            ClassificationResult: 분류 결과

        Raises:
            FileNotFoundError: 이미지 파일이 없을 때
            RuntimeError: 모델 로딩 실패 시
        """
        self._init_model()

        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"이미지 파일 없음: {image_path}")

        try:
            # YOLO predict (verbose=False로 콘솔 출력 억제)
            predict_kwargs = {"source": str(image_path), "verbose": False}
            if self._device:
                predict_kwargs["device"] = self._device

            results = self._model.predict(**predict_kwargs)

            if not results or len(results) == 0:
                logger.warning(f"YOLO-cls 결과 없음: {image_path.name}")
                return ClassificationResult(
                    model_name=self.model_path.name,
                    needs_review=True,
                )

            result = results[0]
            probs = result.probs

            # Top-K 추출
            top_k_indices = probs.top5 if top_k >= 5 else probs.top5[:top_k]
            top_k_confs = probs.top5conf.cpu().tolist()

            top_k_list = []
            for idx, conf in zip(top_k_indices, top_k_confs[:len(top_k_indices)]):
                class_name = self._model.names[idx]
                top_k_list.append((class_name, round(float(conf), 4)))

            # 최상위 예측
            top1_idx = probs.top1
            top1_conf = float(probs.top1conf.cpu())
            top1_name = self._model.names[top1_idx]

            return ClassificationResult(
                category=top1_name,
                confidence=round(top1_conf, 4),
                top_k=top_k_list,
                needs_review=top1_conf < self.confidence_threshold,
                model_name=self.model_path.name,
            )

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"YOLO-cls 추론 실패 ({image_path.name}): {e}")
            return ClassificationResult(
                model_name=self.model_path.name,
                needs_review=True,
            )

    def classify_batch(
        self,
        image_paths: list[str | Path],
        top_k: int = 5,
        batch_size: int = 32,
    ) -> list[ClassificationResult]:
        """
        여러 도면 이미지를 배치로 분류한다.

        Args:
            image_paths: 이미지 파일 경로 리스트
            top_k: 각 이미지의 상위 K개 후보
            batch_size: 배치 크기 (ultralytics 내부 배치)

        Returns:
            list[ClassificationResult]: 입력 순서에 대응하는 분류 결과 리스트
        """
        self._init_model()

        all_results = []
        total = len(image_paths)

        for i in range(0, total, batch_size):
            batch_paths = image_paths[i:i + batch_size]
            batch_str = [str(p) for p in batch_paths]

            try:
                predict_kwargs = {"source": batch_str, "verbose": False}
                if self._device:
                    predict_kwargs["device"] = self._device

                results = self._model.predict(**predict_kwargs)

                for j, result in enumerate(results):
                    probs = result.probs
                    top_k_indices = probs.top5 if top_k >= 5 else probs.top5[:top_k]
                    top_k_confs = probs.top5conf.cpu().tolist()

                    top_k_list = []
                    for idx, conf in zip(top_k_indices, top_k_confs[:len(top_k_indices)]):
                        class_name = self._model.names[idx]
                        top_k_list.append((class_name, round(float(conf), 4)))

                    top1_idx = probs.top1
                    top1_conf = float(probs.top1conf.cpu())
                    top1_name = self._model.names[top1_idx]

                    all_results.append(ClassificationResult(
                        category=top1_name,
                        confidence=round(top1_conf, 4),
                        top_k=top_k_list,
                        needs_review=top1_conf < self.confidence_threshold,
                        model_name=self.model_path.name,
                    ))

                logger.debug(f"배치 분류 완료: {min(i + batch_size, total)}/{total}")

            except Exception as e:
                logger.error(f"배치 분류 실패 (batch {i}~{i + len(batch_paths)}): {e}")
                # 실패한 배치는 개별 처리로 폴백
                for path in batch_paths:
                    try:
                        all_results.append(self.classify(path, top_k=top_k))
                    except Exception as inner_e:
                        logger.error(f"개별 분류도 실패 ({path}): {inner_e}")
                        all_results.append(ClassificationResult(
                            model_name=self.model_path.name,
                            needs_review=True,
                        ))

        return all_results

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
            return True, f"YOLO-cls 정상 ({n}클래스, {self.model_path.name})"
        except Exception as e:
            return False, f"YOLO-cls 로딩 실패: {e}"
