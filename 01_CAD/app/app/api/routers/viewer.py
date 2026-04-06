"""
CAD Vision API — DXF 뷰어 라우터.

DXF → SVG 변환 + 메타데이터 제공.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.utils import (
    ALLOWED_DXF_EXTENSIONS,
    safe_error,
    save_upload,
    validate_file_extension,
    validate_magic_bytes,
)

router = APIRouter(prefix="/api/v1", tags=["viewer"])


# ── 스키마 ──

class DXFLayerInfo(BaseModel):
    """DXF 레이어 정보."""
    name: str
    color: str = "#000000"
    entity_count: int = 0
    visible: bool = True


class DXFBBox(BaseModel):
    """바운딩 박스."""
    min_x: float = 0.0
    min_y: float = 0.0
    max_x: float = 0.0
    max_y: float = 0.0


class DXFViewerResponse(BaseModel):
    """DXF 뷰어 응답 — SVG + 메타데이터."""
    svg: str
    layers: list[DXFLayerInfo] = Field(default_factory=list)
    entities: dict[str, int] = Field(default_factory=dict)
    total_entities: int = 0
    bbox: DXFBBox | None = None


# ── 엔드포인트 ──

@router.post(
    "/viewer/dxf",
    response_model=DXFViewerResponse,
    summary="DXF → SVG 변환 + 메타데이터",
)
async def convert_dxf_to_svg(file: UploadFile = File(...)):
    """DXF 파일을 인터랙티브 SVG + 레이어/엔티티 메타데이터로 변환한다."""
    validate_file_extension(file.filename, ALLOWED_DXF_EXTENSIONS)
    tmp = save_upload(file, suffix=".dxf")
    try:
        validate_magic_bytes(tmp, ".dxf")
        from core.dxf_to_svg import DXFToSVG
        converter = DXFToSVG()
        result = converter.convert(tmp)
        bbox = DXFBBox(**result["bbox"]) if result["bbox"] else None
        layers = [DXFLayerInfo(**l) for l in result["layers"]]
        return DXFViewerResponse(
            svg=result["svg"],
            layers=layers,
            entities=result["entities"],
            total_entities=result["total_entities"],
            bbox=bbox,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise safe_error(e, "DXF→SVG 변환")
    finally:
        tmp.unlink(missing_ok=True)
