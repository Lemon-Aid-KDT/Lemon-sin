"""
CAD Vision REST API — Pydantic v2 스키마.

DrawingPipeline의 dataclass를 REST API 응답/요청 모델로 변환한다.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── 응답 모델 ──


class SimilarDrawingItem(BaseModel):
    """유사도면 알림 항목."""

    drawing_id: str
    score: float
    file_name: str = ""
    file_path: str = ""


class DrawingRecordResponse(BaseModel):
    """등록된 도면 레코드."""

    drawing_id: str
    file_path: str = ""
    file_name: str = ""
    ocr_text: str = ""
    part_numbers: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    category: str = ""
    description: str = ""
    yolo_confidence: float = 0.0
    yolo_needs_review: bool = False
    detected_regions: list[dict] = Field(default_factory=list)
    dxf_path: str = ""
    similar_drawings: list[SimilarDrawingItem] = Field(default_factory=list)
    registered_at: str = ""
    revision: int = 1

    @classmethod
    def from_record(cls, record) -> DrawingRecordResponse:
        """DrawingRecord dataclass → Pydantic 모델 변환."""
        similar = []
        for s in getattr(record, "similar_drawings", []) or []:
            if isinstance(s, dict):
                similar.append(SimilarDrawingItem(**s))
        return cls(
            drawing_id=record.drawing_id,
            file_path=record.file_path,
            file_name=record.file_name,
            ocr_text=record.ocr_text,
            part_numbers=record.part_numbers,
            dimensions=record.dimensions,
            materials=record.materials,
            category=record.category,
            description=record.description,
            yolo_confidence=record.yolo_confidence,
            yolo_needs_review=record.yolo_needs_review,
            detected_regions=record.detected_regions,
            dxf_path=getattr(record, "dxf_path", ""),
            similar_drawings=similar,
            registered_at=getattr(record, "registered_at", ""),
            revision=getattr(record, "revision", 1),
        )


class SearchResultResponse(BaseModel):
    """검색 결과 항목."""

    drawing_id: str
    score: float = 0.0
    distance: float = 0.0
    file_path: str = ""
    file_name: str = ""
    category: str = ""
    metadata: dict = Field(default_factory=dict)

    @classmethod
    def from_result(cls, result) -> SearchResultResponse:
        """SearchResult dataclass → Pydantic 모델 변환."""
        meta = result.metadata or {}
        return cls(
            drawing_id=result.drawing_id,
            score=getattr(result, "score", 0.0),
            distance=getattr(result, "distance", 0.0),
            file_path=meta.get("file_path", ""),
            file_name=meta.get("file_name", ""),
            category=meta.get("category", ""),
            metadata=meta,
        )


class PaginatedResponse(BaseModel):
    """페이지네이션 응답."""

    items: list[DrawingRecordResponse]
    total: int
    page: int
    page_size: int


class StatsResponse(BaseModel):
    """시스템 통계."""

    total_drawings: int = 0
    image_collection_count: int = 0
    text_collection_count: int = 0
    gnn_collection_count: int = 0
    categories: list[str] = Field(default_factory=list)
    category_counts: dict[str, int] = Field(default_factory=dict)
    ollama_status: str = ""
    ollama_model: str = ""
    ollama_healthy: bool = False
    yolo_cls_enabled: bool = False
    yolo_det_enabled: bool = False
    gnn_enabled: bool = False


class DescribeResponse(BaseModel):
    """LLM 분석 응답."""

    drawing_id: str
    description: str


class AskResponse(BaseModel):
    """Q&A 응답."""

    drawing_id: str
    question: str
    answer: str


# ── 요청 모델 ──


class TextSearchRequest(BaseModel):
    """텍스트 검색 요청."""

    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=100)
    category: str = Field(default="", max_length=200)


class AskRequest(BaseModel):
    """Q&A 요청."""

    question: str = Field(..., min_length=1, max_length=2000)


# ── Tier-3 스키마 ──


class DimensionCompareRequest(BaseModel):
    """치수 비교 요청."""

    drawing_id_1: str
    drawing_id_2: str


class DimensionCompareResponse(BaseModel):
    """치수 비교 응답."""

    matched: list[dict] = Field(default_factory=list)
    changed: list[dict] = Field(default_factory=list)
    only_in_a: list[dict] = Field(default_factory=list)
    only_in_b: list[dict] = Field(default_factory=list)
    similarity: float = 0.0


class VersionResponse(BaseModel):
    """부품번호 버전 이력 응답."""

    part_number: str
    versions: list[DrawingRecordResponse]


class BOMEntryResponse(BaseModel):
    """BOM 항목."""

    item_no: int = 0
    part_name: str = ""
    quantity: int = 1
    material: str = ""
    specification: str = ""


class BOMResponse(BaseModel):
    """BOM 추출 응답."""

    entries: list[BOMEntryResponse] = Field(default_factory=list)
    confidence: float = 0.0
    source: str = ""


class DXFDiffResponse(BaseModel):
    """DXF 비교 응답."""

    matched_count: int = 0
    only_in_a_count: int = 0
    only_in_b_count: int = 0
    layer_diff: dict = Field(default_factory=dict)
    summary: dict = Field(default_factory=dict)


# ── Phase 2 추가 스키마 ──


class ClassifyResponse(BaseModel):
    """YOLO 분류 응답."""

    category: str = ""
    confidence: float = 0.0
    needs_review: bool = False
    top_k: list[dict] = Field(default_factory=list)


class PartNumberSearchRequest(BaseModel):
    """부품번호 검색 요청."""

    part_number: str = Field(..., min_length=1, max_length=200)


class ModelInfo(BaseModel):
    """Ollama 모델 정보."""

    name: str
    size: str = ""
    modified: str = ""


class ModelListResponse(BaseModel):
    """Ollama 모델 목록 응답."""

    models: list[ModelInfo] = Field(default_factory=list)


class SettingsUpdateRequest(BaseModel):
    """설정 변경 요청."""

    model: str = Field(..., min_length=1, max_length=200)


class SettingsUpdateResponse(BaseModel):
    """설정 변경 응답."""

    status: str = "ok"
    model: str = ""


class VersionHistoryResponse(BaseModel):
    """전체 버전 이력 응답."""

    versions: dict[str, int] = Field(default_factory=dict)
    total_parts: int = 0


# ── v5.4 통합 검색 ──


class UnifiedSearchRequest(BaseModel):
    """통합 검색 요청 (v5.4)."""

    text: str = Field(default="", max_length=1000, description="텍스트 쿼리")
    part_number: str = Field(default="", max_length=200, description="부품번호")
    channels: list[str] = Field(
        default=["text", "image"],
        description="검색 채널: text, image, gnn, part_number",
    )
    top_k: int = Field(default=10, ge=1, le=100)
    category: str = Field(default="", max_length=200)


class UnifiedSearchResultResponse(BaseModel):
    """통합 검색 결과 단건 (v5.4)."""

    record_id: str
    score: float = 0.0
    channel_scores: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    thumbnail_path: str = ""

    @classmethod
    def from_unified(cls, r) -> UnifiedSearchResultResponse:
        """UnifiedSearchResult → Pydantic 변환."""
        return cls(
            record_id=r.record_id,
            score=r.score,
            channel_scores=r.channel_scores,
            metadata=r.metadata,
            thumbnail_path=r.thumbnail_path or "",
        )
