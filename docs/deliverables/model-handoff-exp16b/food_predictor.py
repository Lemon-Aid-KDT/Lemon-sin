"""exp16b 음식 탐지 모델 배포 래퍼 — 지원 40클래스.

모델(best.pt)은 50클래스로 학습되어 있고, 서비스 지원 범위는 40클래스다.
미지원 10클래스는 **추론 시 classes 인자로 제외**한다 (재학습·모델 수정 불필요).
이 방식은 wild 739장 시뮬레이션으로 검증됨: 제외해도 지원 클래스 결과는 변하지 않음.

Usage:
    from food_predictor import FoodPredictor

    fp = FoodPredictor("best.pt")           # exp16b_deploy_config.json이 같은 폴더에 있어야 함
    top1 = fp.predict_top1("photo.jpg")
    if top1 is None:
        print("음식을 인식하지 못했어요. 다시 찍어주세요.")
    else:
        print(top1["name"], top1["conf"], top1["xyxy"])
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ultralytics import YOLO


class FoodPredictor:
    """exp16b best.pt를 지원 40클래스로 추론하는 래퍼.

    Attributes:
        config: 배포 설정(exp16b_deploy_config.json) dict.
        model: 로드된 ultralytics YOLO 모델 (50클래스).
    """

    def __init__(self, weights: str | Path, config_path: str | Path | None = None) -> None:
        """모델과 배포 설정을 로드한다.

        Args:
            weights: exp16b best.pt 경로.
            config_path: 배포 설정 JSON 경로. 생략 시 이 파일과 같은 폴더의
                exp16b_deploy_config.json 사용.

        Raises:
            FileNotFoundError: weights 또는 config 파일이 없는 경우.
            ValueError: 모델 클래스 수가 설정(nc_model=50)과 다른 경우.
        """
        cfg_path = Path(config_path) if config_path else Path(__file__).parent / "exp16b_deploy_config.json"
        self.config: dict[str, Any] = json.loads(cfg_path.read_text(encoding="utf-8"))
        self.model = YOLO(str(weights))
        if len(self.model.names) != self.config["nc_model"]:
            raise ValueError(
                f"모델 클래스 수 {len(self.model.names)} != 설정 {self.config['nc_model']} — "
                "다른 .pt를 로드했는지 확인하세요."
            )
        self._classes: list[int] = self.config["supported_class_indices"]
        self._conf: float = self.config["recommended_conf"]

    def predict_top1(self, image: Any, conf: float | None = None) -> dict[str, Any] | None:
        """이미지에서 최고 신뢰도의 지원 클래스 음식 1개를 반환한다.

        미지원 10클래스는 추론 단계에서 제외되므로 결과에 나타나지 않는다.

        Args:
            image: 이미지 경로(str/Path) 또는 ndarray 등 ultralytics가 받는 입력.
            conf: 최소 신뢰도. 생략 시 설정값(0.10) 사용.

        Returns:
            {"name": 클래스명, "conf": 신뢰도, "xyxy": [x1, y1, x2, y2]} 또는
            지원 음식을 찾지 못하면 None (앱에서 "인식 불가" 안내 권장).
        """
        threshold = self._conf if conf is None else conf
        r = self.model.predict(image, conf=threshold, classes=self._classes, verbose=False)[0]
        if not len(r.boxes):
            return None
        best = int(r.boxes.conf.argmax())
        return {
            "name": self.model.names[int(r.boxes.cls[best])],
            "conf": float(r.boxes.conf[best]),
            "xyxy": [float(v) for v in r.boxes.xyxy[best]],
        }

    def predict_all(self, image: Any, conf: float | None = None) -> list[dict[str, Any]]:
        """이미지의 모든 지원 클래스 박스를 신뢰도 내림차순으로 반환한다 (다중 음식용).

        Args:
            image: 이미지 입력 (predict_top1과 동일).
            conf: 최소 신뢰도. 생략 시 설정값(0.10).

        Returns:
            [{"name", "conf", "xyxy"}, ...] — 없으면 빈 리스트.
        """
        threshold = self._conf if conf is None else conf
        r = self.model.predict(image, conf=threshold, classes=self._classes, verbose=False)[0]
        out = [
            {
                "name": self.model.names[int(r.boxes.cls[i])],
                "conf": float(r.boxes.conf[i]),
                "xyxy": [float(v) for v in r.boxes.xyxy[i]],
            }
            for i in range(len(r.boxes))
        ]
        return sorted(out, key=lambda b: -b["conf"])
