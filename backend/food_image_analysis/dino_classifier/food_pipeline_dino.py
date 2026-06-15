# -*- coding: utf-8 -*-
"""실전 음식 분석 파이프라인 — 디텍터 + DINOv3 분류기 (방해음식 마스킹).

구조:
  1) 디텍터(1-class)로 음식 위치 박스 전부 검출
  2) 분기:
     - 박스 0개  → "음식 없음"
     - 박스 1개  → 풀이미지 분류 (단일요리, 가장 정확)
     - 박스 여러개 → 각 음식을 분류할 때 '나머지 음식 박스만 회색 마스킹' 후 전체 분류
                     (정수님 아이디어, wild 검증: 타이트크롭 0.72 vs 마스킹 0.84)
  3) 겹침 처리: 타겟 박스 영역은 원본 복원(다른 박스 마스크가 타겟을 가리지 않게)

분류기 = DINOv3-vitb16 + 선형 프로브(train_probe.py로 저장한 probe_head.pt).
디텍터 = 인계 detector_best.pt (1-class food).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw
from transformers import AutoImageProcessor, AutoModel
from ultralytics import YOLO

HERE = Path(__file__).resolve().parent
DETECTOR = HERE.parent / "detector" / "detector_best.pt"
PROBE = HERE / "probe_head.pt"

# 영문 → 한글 표시명
KR = {
    "barbecue-ribs": "갈비", "black-bean-noodles": "짜장면", "braised-chicken": "찜닭",
    "braised-pork-hock": "족발", "bread": "빵", "bulgogi": "불고기", "cake": "케이크",
    "cold-noodles": "냉면", "curry": "카레", "dim-sum": "딤섬", "fish-cake": "어묵",
    "fried-chicken": "후라이드치킨", "fried-food-platter": "튀김(모둠)", "grilled-fish": "생선구이",
    "grilled-pork-belly": "삼겹살", "hamburger": "햄버거", "korean-blood-sausage": "순대",
    "mixed-rice-bowl": "비빔밥", "pasta": "파스타", "pizza": "피자", "raw-fish": "회",
    "rice-porridge": "죽", "rice-soup": "국밥", "salad": "샐러드", "sandwich": "샌드위치",
    "savory-pancake": "전/부침개", "seaweed-rice-roll": "김밥", "spicy-mixed-noodles": "비빔국수",
    "sushi": "초밥", "takoyaki": "타코야키", "udon": "우동", "western-cream-soup": "양식수프",
    "japanese-ramen": "일본라멘", "korean-ramyeon-red": "라면", "tteokbokki-red": "떡볶이",
    "pork-cutlet-dry": "돈가스", "kalguksu": "칼국수", "rice-noodle-soup": "쌀국수",
    "jjigae-red": "빨간찌개", "doenjang-jjigae": "된장찌개",
}


def kr(name: str) -> str:
    """영문 클래스명을 한글 표시명으로 변환한다 (없으면 원문)."""
    return KR.get(name, name)


class FoodPipeline:
    """디텍터 + DINOv3 마스킹 분류 파이프라인.

    Attributes:
        det: 1-class 음식 디텍터(YOLO).
        dino: DINOv3 백본(특징 추출, 동결).
        proc: DINOv3 이미지 프로세서.
        lin: 선형 분류기(40종).
        classes: 분류 클래스명 리스트.
    """

    def __init__(self, detector_path: str | Path = DETECTOR, probe_path: str | Path = PROBE,
                 det_conf: float = 0.30, max_px: int = 896, min_cls_conf: float = 0.15,
                 min_area_frac: float = 0.04, max_foods: int = 6) -> None:
        """디텍터·DINOv3·프로브를 로드한다.

        Args:
            detector_path: 1-class 음식 디텍터 가중치.
            probe_path: train_probe.py가 저장한 probe_head.pt.
            det_conf: 디텍터 신뢰도 임계값.
            max_px: 분류 전 이미지 축소 상한(모델 내부 224라 무손실).

        Raises:
            FileNotFoundError: 디텍터 또는 프로브 파일이 없는 경우.
        """
        if not Path(detector_path).exists():
            raise FileNotFoundError(f"디텍터 없음: {detector_path}")
        if not Path(probe_path).exists():
            raise FileNotFoundError(f"프로브 없음: {probe_path} — 먼저 train_probe.py 실행")
        self.dev = "cuda" if torch.cuda.is_available() else "cpu"
        self.det = YOLO(str(detector_path))
        self.det_conf = det_conf
        self.max_px = max_px
        self.min_cls_conf = min_cls_conf  # 이 분류신뢰도 미만 음식은 헛박스로 보고 제외
        self.min_area_frac = min_area_frac  # 이미지 면적의 이 비율 미만 박스=반찬종지로 보고 제외
        self.max_foods = max_foods  # 메인 요리 최대 개수(과탐지 폭주 방지)
        ckpt = torch.load(probe_path, map_location=self.dev, weights_only=False)
        self.classes: list[str] = ckpt["classes"]
        self.proc = AutoImageProcessor.from_pretrained(ckpt["dino_id"])
        self.dino = AutoModel.from_pretrained(ckpt["dino_id"]).to(self.dev).eval()
        self.lin = torch.nn.Linear(ckpt["feat_dim"], len(self.classes)).to(self.dev)
        self.lin.load_state_dict(ckpt["state_dict"]); self.lin.eval()

    @torch.no_grad()
    def _classify(self, im: Image.Image) -> tuple[str, float]:
        """이미지 1장을 DINOv3+프로브로 분류한다 → (영문클래스, 신뢰도)."""
        x = im.copy(); x.thumbnail((self.max_px, self.max_px))
        inp = self.proc(images=x, return_tensors="pt").to(self.dev)
        o = self.dino(**inp)
        f = getattr(o, "pooler_output", None)
        if f is None:
            f = o.last_hidden_state[:, 0]
        f = f / f.norm(dim=-1, keepdim=True)
        prob = self.lin(f).softmax(-1)[0]
        i = int(prob.argmax())
        return self.classes[i], float(prob[i])

    @staticmethod
    def _iou(a, b) -> float:
        """두 xyxy 박스의 IoU."""
        x1, y1 = max(a[0], b[0]), max(a[1], b[1])
        x2, y2 = min(a[2], b[2]), min(a[3], b[3])
        inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
        ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
        return inter / ua if ua > 0 else 0.0

    def _detect(self, im: Image.Image) -> list[list[float]]:
        """음식 박스 검출 → 겹침 병합(IoU>0.6) + 작은 반찬종지 제외(면적) + 개수 캡.

        반찬은 음식이라 food/not-food 필터로 못 거름 → '반찬 종지는 작다'는 점을 이용해
        이미지 면적의 min_area_frac 미만 박스를 메인요리가 아닌 것으로 보고 제외.
        """
        r = self.det.predict(im, conf=self.det_conf, iou=0.15, agnostic_nms=True,
                             max_det=50, imgsz=512, verbose=False)[0]
        order = r.boxes.conf.argsort(descending=True).cpu().numpy() if len(r.boxes) else []
        boxes = [[float(v) for v in r.boxes.xyxy[i]] for i in order]  # conf 내림차순
        W, H = im.size
        min_area = self.min_area_frac * W * H
        kept: list[list[float]] = []
        for b in boxes:
            area = (b[2] - b[0]) * (b[3] - b[1])
            if area < min_area:
                continue  # 반찬 종지 등 작은 박스 제외
            if all(self._iou(b, k) <= 0.6 for k in kept):
                kept.append(b)
            if len(kept) >= self.max_foods:
                break
        return kept

    @staticmethod
    def _mask_others(im: Image.Image, boxes: list[list[float]], target: int) -> Image.Image:
        """타겟 외 박스를 회색 마스킹하되, 타겟 영역은 원본 복원(겹침 처리)."""
        out = im.copy()
        d = ImageDraw.Draw(out)
        for j, b in enumerate(boxes):
            if j != target:
                d.rectangle(b, fill=(128, 128, 128))
        tx1, ty1, tx2, ty2 = (int(v) for v in boxes[target])
        out.paste(im.crop((tx1, ty1, tx2, ty2)), (tx1, ty1))  # 타겟 원본 복원
        return out

    def analyze(self, im: Image.Image) -> list[dict]:
        """이미지에서 음식들을 검출·분류한다.

        Args:
            im: PIL RGB 이미지.

        Returns:
            음식별 dict 리스트 [{box, name_en, name_ko, conf, det_conf}].
            음식이 없으면 빈 리스트.
        """
        im = im.convert("RGB")
        return self.classify_boxes(im, self._detect(im))

    def classify_boxes(self, im: Image.Image, boxes: list[list[float]]) -> list[dict]:
        """주어진 박스들을 마스킹 분류한다(탐지기 무관 — YOLO/Grounding DINO 등 어디서 온 박스든).

        Args:
            im: PIL RGB 이미지.
            boxes: [x1,y1,x2,y2] 리스트.

        Returns:
            음식별 dict 리스트 [{box, name_en, name_ko, conf}] (분류신뢰도 내림차순).
        """
        im = im.convert("RGB")
        if not boxes:
            return []
        results = []
        for i, box in enumerate(boxes):
            # 하이브리드: 박스 1개면 풀이미지, 여러개면 나머지 마스킹
            target_img = im if len(boxes) == 1 else self._mask_others(im, boxes, i)
            name, conf = self._classify(target_img)
            results.append({"box": box, "name_en": name, "name_ko": kr(name), "conf": conf})
        # 분류신뢰도 낮은 헛박스 제외. 단, 전부 낮으면 최고 1개는 남김(빈 결과 방지)
        strong = [r for r in results if r["conf"] >= self.min_cls_conf]
        if strong:
            return sorted(strong, key=lambda r: -r["conf"])
        return [max(results, key=lambda r: r["conf"])]
