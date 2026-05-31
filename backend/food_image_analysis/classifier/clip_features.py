"""
공유 CLIP 백본 모듈
====================
카스케이드의 모든 단계(is_food, cuisine, meal_component ...)가
이 한 곳에서 만든 768차원 임베딩을 공유한다.

- 무거운 백본(CLIP ViT-L/14)은 여기서 '딱 한 번'만 돈다.
- 각 단계의 분류기 헤드는 이 벡터만 받아 쓰는 경량 모델이다.

다른 스크립트에서:
    from clip_features import CLIPEncoder
    enc = CLIPEncoder()
    vec = enc.embed_paths([img_path])     # (N, 768) L2 정규화된 float32
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

# 기존 파이프라인과 동일한 백본 (이미 로컬 캐시에 있음 → 추가 다운로드 없음)
MODEL_NAME = "openai/clip-vit-large-patch14"
EMBED_DIM = 768
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class CLIPEncoder:
    """이미지 → L2 정규화된 CLIP 임베딩."""

    def __init__(self, model_name: str = MODEL_NAME, device: str | None = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model.eval()
        self.model_name = model_name

    @torch.no_grad()
    def embed_images(self, images: list[Image.Image]) -> np.ndarray:
        """PIL 이미지 리스트 → (N, 768) float32, L2 정규화.

        transformers 버전별 get_image_features 반환형 차이를 피하려고
        기존 파이프라인과 동일하게 vision_model + visual_projection 을 직접 호출한다.
        """
        if not images:
            return np.empty((0, EMBED_DIM), dtype=np.float32)
        inputs = self.processor(images=images, return_tensors="pt").to(self.device)
        out = self.model.vision_model(pixel_values=inputs["pixel_values"])
        feats = self.model.visual_projection(out.pooler_output)
        feats = feats / feats.norm(dim=-1, keepdim=True)
        return feats.cpu().numpy().astype(np.float32)

    def embed_paths(
        self,
        paths: Iterable[Path | str],
        batch_size: int = 16,
    ) -> tuple[np.ndarray, list[Path]]:
        """이미지 경로들 → (임베딩 배열, 성공한 경로 리스트).

        깨진/열리지 않는 이미지는 건너뛴다.
        """
        paths = [Path(p) for p in paths]
        all_vecs: list[np.ndarray] = []
        ok_paths: list[Path] = []

        for start in range(0, len(paths), batch_size):
            batch = paths[start : start + batch_size]
            imgs, valid = [], []
            for p in batch:
                try:
                    imgs.append(Image.open(p).convert("RGB"))
                    valid.append(p)
                except Exception:
                    pass  # 손상 이미지 무시
            if not imgs:
                continue
            all_vecs.append(self.embed_images(imgs))
            ok_paths.extend(valid)

        if not all_vecs:
            return np.empty((0, EMBED_DIM), dtype=np.float32), []
        return np.concatenate(all_vecs, axis=0), ok_paths


def iter_image_paths(root: Path) -> list[Path]:
    """root 아래 모든 이미지 경로 (빈 파일 제외)."""
    return [
        p
        for p in root.rglob("*")
        if p.suffix.lower() in IMAGE_EXTENSIONS and p.is_file() and p.stat().st_size > 0
    ]
