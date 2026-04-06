"""v5.4 통합 데이터 모델 정의.

기존 DrawingRecord(pipeline.py)와 SearchResult(vector_store.py)는 유지하면서,
새로운 통합 엔진(CAD Router, Search Engine, VLM Orchestrator, Comparison Engine,
Universal Renderer)이 사용할 DTO를 정의합니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SearchChannel(Enum):
    """검색 채널 유형."""
    TEXT = "text"
    IMAGE = "image"
    GNN = "gnn"
    PART_NUMBER = "part_number"


class CompareMode(Enum):
    """비교 모드."""
    DXF_STRUCTURE = "dxf_structure"
    DIMENSIONS = "dimensions"
    VISUAL_DIFF = "visual_diff"
    METADATA = "metadata"


class RenderMode(Enum):
    """렌더링 모드."""
    THUMBNAIL = "thumbnail"   # 256×256
    FULL = "full"             # 1024×1024
    INTERACTIVE = "interactive"  # HTML viewer


class AnalysisTask(Enum):
    """VLM 분석 작업 유형."""
    DESCRIBE = "describe"
    CLASSIFY = "classify"
    EXTRACT_META = "extract_meta"
    BOM = "bom"


# ---------------------------------------------------------------------------
# CAD Router DTOs
# ---------------------------------------------------------------------------

@dataclass
class ProcessableResult:
    """CAD Router 변환 결과 DTO.

    ensure_processable()의 반환값으로,
    임의 CAD 포맷을 PNG + 메타데이터로 변환한 결과를 담습니다.
    """
    status: str                     # "ready" | "converted" | "unsupported"
    png_path: Optional[str] = None
    dxf_path: Optional[str] = None  # GNN 임베딩용 (DXF 원본일 때만)
    source_format: str = ""
    metadata: dict = field(default_factory=dict)
    guidance: Optional[str] = None  # 미지원 포맷 시 사용자 안내 메시지


# ---------------------------------------------------------------------------
# ExtractedFacts — 등록 시 1회 추출, 이후 재사용
# ---------------------------------------------------------------------------

@dataclass
class ExtractedFacts:
    """도면에서 추출한 팩트 모음.

    등록(register) 시 한 번 추출하여 저장하고,
    분석/검색/비교 등 모든 후속 작업에서 재사용합니다.
    """
    # OCR 추출
    part_numbers: list = field(default_factory=list)
    materials: list = field(default_factory=list)
    dimensions: list = field(default_factory=list)
    ocr_full_text: str = ""

    # YOLO 분류
    yolo_category: str = ""
    yolo_confidence: float = 0.0
    yolo_top5: list = field(default_factory=list)  # [(category, confidence), ...]

    # YOLO 탐지
    detected_regions: list = field(default_factory=list)  # [{"type", "bbox", "confidence"}]

    # DXF 메타데이터 (DXF 원본인 경우)
    dxf_metadata: Optional[dict] = None  # entity_types, layer_count, bbox, aspect_ratio

    # 원본 파일 정보
    source_format: str = ""
    file_size_bytes: int = 0

    def to_dict(self) -> dict:
        """직렬화용 딕셔너리 변환."""
        return {
            "part_numbers": self.part_numbers,
            "materials": self.materials,
            "dimensions": self.dimensions,
            "ocr_full_text": self.ocr_full_text,
            "yolo_category": self.yolo_category,
            "yolo_confidence": self.yolo_confidence,
            "yolo_top5": self.yolo_top5,
            "detected_regions": self.detected_regions,
            "dxf_metadata": self.dxf_metadata,
            "source_format": self.source_format,
            "file_size_bytes": self.file_size_bytes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ExtractedFacts:
        """딕셔너리에서 복원."""
        if not data:
            return cls()
        return cls(
            part_numbers=data.get("part_numbers", []),
            materials=data.get("materials", []),
            dimensions=data.get("dimensions", []),
            ocr_full_text=data.get("ocr_full_text", ""),
            yolo_category=data.get("yolo_category", ""),
            yolo_confidence=data.get("yolo_confidence", 0.0),
            yolo_top5=data.get("yolo_top5", []),
            detected_regions=data.get("detected_regions", []),
            dxf_metadata=data.get("dxf_metadata"),
            source_format=data.get("source_format", ""),
            file_size_bytes=data.get("file_size_bytes", 0),
        )

    @classmethod
    def from_drawing_record(cls, rec) -> ExtractedFacts:
        """기존 DrawingRecord(pipeline.py)에서 변환.

        기존 레코드와의 호환을 위해 필드를 매핑합니다.
        """
        return cls(
            part_numbers=getattr(rec, "part_numbers", []) or [],
            materials=getattr(rec, "materials", []) or [],
            dimensions=getattr(rec, "dimensions", []) or [],
            ocr_full_text=getattr(rec, "ocr_text", ""),
            yolo_category=getattr(rec, "category", ""),
            yolo_confidence=getattr(rec, "yolo_confidence", 0.0),
            yolo_top5=getattr(rec, "yolo_top_k", []) or [],
            detected_regions=getattr(rec, "detected_regions", []) or [],
            dxf_metadata=None,
            source_format="dxf" if getattr(rec, "dxf_path", "") else "png",
            file_size_bytes=0,
        )


# ---------------------------------------------------------------------------
# Unified Search DTOs
# ---------------------------------------------------------------------------

@dataclass
class SearchQuery:
    """통합 검색 쿼리 DTO.

    4가지 검색 채널(text, image, gnn, part_number)을 하나의 인터페이스로 통합합니다.
    """
    text: Optional[str] = None
    image_path: Optional[str] = None
    dxf_path: Optional[str] = None
    part_number: Optional[str] = None
    channels: list = field(default_factory=lambda: [
        SearchChannel.TEXT, SearchChannel.IMAGE,
    ])
    channel_weights: Optional[dict] = None  # 채널별 가중치 오버라이드
    top_k: int = 10
    filters: dict = field(default_factory=dict)  # {material, format, category}


@dataclass
class UnifiedSearchResult:
    """통합 검색 결과 단건.

    기존 SearchResult(vector_store.py)와 구분하기 위해 UnifiedSearchResult로 명명합니다.
    """
    record_id: str
    score: float                    # 통합 유사도 점수 (0~1)
    channel_scores: dict = field(default_factory=dict)  # {text: 0.8, image: 0.3, ...}
    metadata: dict = field(default_factory=dict)
    thumbnail_path: Optional[str] = None


# ---------------------------------------------------------------------------
# Comparison DTOs
# ---------------------------------------------------------------------------

@dataclass
class CompareInput:
    """비교 대상 도면 쌍."""
    left_record_id: str
    right_record_id: str
    mode: CompareMode
    options: dict = field(default_factory=dict)


@dataclass
class CompareResult:
    """통합 비교 결과 DTO."""
    mode: CompareMode
    similarity_score: float             # 0~1
    summary: str = ""
    details: dict = field(default_factory=dict)
    left_thumbnail: Optional[str] = None
    right_thumbnail: Optional[str] = None


# ---------------------------------------------------------------------------
# Universal Renderer DTOs
# ---------------------------------------------------------------------------

@dataclass
class RenderResult:
    """렌더링 결과."""
    mode: RenderMode
    png_path: Optional[str] = None       # THUMBNAIL, FULL 모드
    html_viewer: Optional[str] = None    # INTERACTIVE 모드
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# VLM Orchestrator DTOs
# ---------------------------------------------------------------------------

@dataclass
class AnalysisResult:
    """VLM 통합 분석 결과."""
    description: Optional[str] = None
    category: Optional[str] = None
    category_confidence: float = 0.0
    metadata: dict = field(default_factory=dict)
    bom: Optional[list] = None
    hallucination_flags: list = field(default_factory=list)
    processing_time_ms: int = 0
