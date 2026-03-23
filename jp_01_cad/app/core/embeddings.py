"""
도면 임베딩 생성 모듈

- 이미지 임베딩: OpenCLIP (ViT-L/14, 768-dim) 모델로 도면 이미지를 벡터화
- 텍스트 임베딩: SentenceTransformer로 검색 쿼리 및 OCR 텍스트를 벡터화
"""

from pathlib import Path

import numpy as np
import torch
from loguru import logger
from PIL import Image


class ImageEmbedder:
    """OpenCLIP 기반 이미지 임베딩 생성기

    OpenCLIP은 SigLIP sigmoid loss를 지원하여 작은 배치에서도
    효과적인 fine-tuning이 가능하다 (InfoNCE의 배치 크기 제약 해소).
    """

    def __init__(
        self,
        model_name: str = "ViT-L-14",
        pretrained: str = "datacomp_xl_s13b_b90k",
        device: str | None = None,
        finetuned_path: str = "",
    ):
        """
        Args:
            model_name: OpenCLIP 모델 아키텍처 (ViT-L-14, ViT-B-32 등)
            pretrained: 사전학습 체크포인트 (datacomp_xl_s13b_b90k, openai 등)
            device: 연산 디바이스 (None이면 자동 선택)
            finetuned_path: Fine-tuned 체크포인트 경로 (빈 문자열이면 pre-trained)
        """
        self.model_name = model_name
        self.pretrained = pretrained
        self.device = device or self._select_device()
        self.finetuned_path = finetuned_path
        self._model = None
        self._preprocess = None
        self._tokenizer = None

    @staticmethod
    def _select_device() -> str:
        """사용 가능한 최적 디바이스 선택"""
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _init_model(self):
        """OpenCLIP 모델 지연 로딩 (fine-tuned weights 지원)"""
        if self._model is not None:
            return

        try:
            import open_clip

            logger.info(
                f"OpenCLIP 모델 로딩: {self.model_name} "
                f"(pretrained={self.pretrained}) on {self.device}"
            )
            self._model, _, self._preprocess = open_clip.create_model_and_transforms(
                self.model_name,
                pretrained=self.pretrained,
                device=self.device,
            )
            self._tokenizer = open_clip.get_tokenizer(self.model_name)

            # Fine-tuned 체크포인트 로딩 (있으면)
            if self.finetuned_path and Path(self.finetuned_path).exists():
                logger.info(f"Fine-tuned OpenCLIP 가중치 로딩: {self.finetuned_path}")
                checkpoint = torch.load(
                    self.finetuned_path, map_location="cpu"
                )
                state_dict = checkpoint.get("model_state_dict", checkpoint)
                self._model.load_state_dict(state_dict)
                self._model = self._model.to(self.device)
                logger.info("Fine-tuned OpenCLIP 가중치 로딩 완료")
            elif self.finetuned_path:
                logger.warning(
                    f"Fine-tuned OpenCLIP 체크포인트 없음 (pre-trained 사용): "
                    f"{self.finetuned_path}"
                )

            self._model.eval()
            logger.info("OpenCLIP 모델 로딩 완료")
        except ImportError:
            raise RuntimeError(
                "OpenCLIP 미설치: pip install open-clip-torch>=2.26.0"
            )
        except RuntimeError as e:
            if "out of memory" in str(e).lower() or "CUDA" in str(e):
                logger.error(f"GPU 메모리 부족으로 OpenCLIP 로딩 실패, CPU로 재시도: {e}")
                import open_clip

                self.device = "cpu"
                self._model, _, self._preprocess = open_clip.create_model_and_transforms(
                    self.model_name, pretrained=self.pretrained, device="cpu",
                )
                self._tokenizer = open_clip.get_tokenizer(self.model_name)
                if self.finetuned_path and Path(self.finetuned_path).exists():
                    checkpoint = torch.load(self.finetuned_path, map_location="cpu")
                    state_dict = checkpoint.get("model_state_dict", checkpoint)
                    self._model.load_state_dict(state_dict)
                self._model.eval()
                logger.info("OpenCLIP 모델 CPU 로딩 완료 (GPU 메모리 부족)")
            else:
                raise RuntimeError(f"OpenCLIP 모델 로딩 실패: {e}") from e

    def embed_image(self, image_path: str | Path) -> np.ndarray:
        """
        단일 도면 이미지를 벡터로 변환한다.

        Args:
            image_path: 이미지 파일 경로

        Returns:
            np.ndarray: 정규화된 임베딩 벡터 (768차원 for ViT-L-14)
        """
        self._init_model()
        image = Image.open(image_path).convert("RGB")
        image_tensor = self._preprocess(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            embedding = self._model.encode_image(image_tensor)
            embedding = embedding / embedding.norm(dim=-1, keepdim=True)

        return embedding.cpu().numpy().flatten()

    def embed_images_batch(self, image_paths: list[str | Path], batch_size: int = 16) -> list[np.ndarray]:
        """
        여러 도면 이미지를 배치로 벡터화한다.

        Args:
            image_paths: 이미지 파일 경로 리스트
            batch_size: 배치 크기

        Returns:
            list[np.ndarray]: 임베딩 벡터 리스트
        """
        self._init_model()
        all_embeddings = []

        for i in range(0, len(image_paths), batch_size):
            batch_paths = image_paths[i:i + batch_size]
            images = []
            for path in batch_paths:
                try:
                    img = Image.open(path).convert("RGB")
                    images.append(self._preprocess(img))
                except Exception as e:
                    logger.warning(f"이미지 로딩 실패 ({path}): {e}")
                    # 실패 시 빈 이미지로 대체
                    images.append(self._preprocess(Image.new("RGB", (224, 224))))

            batch_tensor = torch.stack(images).to(self.device)

            try:
                with torch.no_grad():
                    embeddings = self._model.encode_image(batch_tensor)
                    embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)

                for emb in embeddings.cpu().numpy():
                    all_embeddings.append(emb.flatten())
            except RuntimeError as e:
                if "out of memory" in str(e).lower():
                    logger.warning(f"GPU OOM 발생, 배치 크기 줄여 재시도 (batch_size={len(images)}→1)")
                    torch.cuda.empty_cache() if torch.cuda.is_available() else None
                    # 개별 처리로 폴백
                    for img_tensor in images:
                        with torch.no_grad():
                            emb = self._model.encode_image(img_tensor.unsqueeze(0).to(self.device))
                            emb = emb / emb.norm(dim=-1, keepdim=True)
                        all_embeddings.append(emb.cpu().numpy().flatten())
                else:
                    raise

            logger.debug(f"배치 임베딩 완료: {i + len(batch_paths)}/{len(image_paths)}")

        return all_embeddings

    def embed_text(self, text: str) -> np.ndarray:
        """
        OpenCLIP 텍스트 인코더로 텍스트를 벡터화한다.
        이미지-텍스트 크로스모달 검색에 사용한다.

        Args:
            text: 검색 쿼리 텍스트

        Returns:
            np.ndarray: 정규화된 텍스트 임베딩 벡터 (768차원 for ViT-L-14)
        """
        self._init_model()

        text_token = self._tokenizer([text]).to(self.device)

        with torch.no_grad():
            embedding = self._model.encode_text(text_token)
            embedding = embedding / embedding.norm(dim=-1, keepdim=True)

        return embedding.cpu().numpy().flatten()


class TextEmbedder:
    """SentenceTransformer 기반 텍스트 임베딩 생성기

    E5 계열 모델(intfloat/multilingual-e5-*)은 비대칭 검색에 최적화되어
    query/passage prefix를 자동 적용한다:
      - 검색 쿼리: "query: {text}"
      - 저장 텍스트: "passage: {text}"
    """

    # E5 prefix가 필요한 모델 패턴
    _E5_PREFIXES = ("intfloat/e5-", "intfloat/multilingual-e5-")

    def __init__(self, model_name: str = "intfloat/multilingual-e5-small"):
        """
        Args:
            model_name: SentenceTransformer 모델명
        """
        self.model_name = model_name
        self._model = None
        self._needs_prefix = any(model_name.startswith(p) for p in self._E5_PREFIXES)

    def _init_model(self):
        """모델 지연 로딩"""
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"텍스트 임베딩 모델 로딩: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            logger.info(
                f"텍스트 임베딩 모델 로딩 완료 "
                f"(dim={self._model.get_sentence_embedding_dimension()}, "
                f"prefix={'E5' if self._needs_prefix else 'none'})"
            )
        except ImportError:
            raise RuntimeError("sentence-transformers 미설치: pip install sentence-transformers")
        except RuntimeError as e:
            raise RuntimeError(f"텍스트 임베딩 모델 로딩 실패: {e}") from e

    def _add_prefix(self, text: str, prefix_type: str = "query") -> str:
        """E5 모델용 prefix 추가 (이미 있으면 스킵)"""
        if not self._needs_prefix:
            return text
        if text.startswith("query: ") or text.startswith("passage: "):
            return text
        return f"{prefix_type}: {text}"

    def embed(self, text: str) -> np.ndarray:
        """
        단일 텍스트를 벡터로 변환한다 (검색 쿼리용, "query:" prefix 자동 적용).

        Args:
            text: 입력 텍스트 (검색 쿼리)

        Returns:
            np.ndarray: 임베딩 벡터 (384차원)
        """
        self._init_model()
        text = self._add_prefix(text, "query")
        embedding = self._model.encode(text, normalize_embeddings=True)
        return np.array(embedding).flatten()

    def embed_passage(self, text: str) -> np.ndarray:
        """
        저장용 텍스트를 벡터로 변환한다 ("passage:" prefix 자동 적용).

        Args:
            text: 저장할 텍스트 (도면 OCR 텍스트 + 카테고리)

        Returns:
            np.ndarray: 임베딩 벡터 (384차원)
        """
        self._init_model()
        text = self._add_prefix(text, "passage")
        embedding = self._model.encode(text, normalize_embeddings=True)
        return np.array(embedding).flatten()

    def embed_batch(self, texts: list[str], batch_size: int = 32,
                    prefix_type: str = "query") -> list[np.ndarray]:
        """
        여러 텍스트를 배치로 벡터화한다.

        Args:
            texts: 텍스트 리스트
            batch_size: 배치 크기
            prefix_type: "query" (검색용) 또는 "passage" (저장용)

        Returns:
            list[np.ndarray]: 임베딩 벡터 리스트
        """
        self._init_model()
        prefixed = [self._add_prefix(t, prefix_type) for t in texts]
        try:
            embeddings = self._model.encode(
                prefixed,
                batch_size=batch_size,
                normalize_embeddings=True,
                show_progress_bar=True,
            )
            return [emb.flatten() for emb in embeddings]
        except Exception as e:
            logger.error(f"배치 텍스트 임베딩 실패 ({len(texts)}건): {e}")
            raise
