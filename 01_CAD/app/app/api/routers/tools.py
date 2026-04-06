"""
CAD Vision API — 도구 라우터.

치수 비교, 버전 이력, BOM 추출, DXF 비교.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.api.dependencies import get_pipeline
from app.api.schemas import (
    BOMEntryResponse,
    BOMResponse,
    DimensionCompareRequest,
    DimensionCompareResponse,
    DrawingRecordResponse,
    DXFDiffResponse,
    VersionHistoryResponse,
    VersionResponse,
)
from app.api.utils import (
    ALLOWED_DXF_EXTENSIONS,
    safe_error,
    save_upload,
    validate_file_extension,
    validate_magic_bytes,
)

router = APIRouter(prefix="/api/v1", tags=["tools"])


@router.post(
    "/drawings/compare/dimensions",
    response_model=DimensionCompareResponse,
)
async def compare_dimensions(req: DimensionCompareRequest, pipeline=Depends(get_pipeline)):
    """두 도면의 치수를 비교한다."""
    try:
        result = pipeline.compare_dimensions(req.drawing_id_1, req.drawing_id_2)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return DimensionCompareResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise safe_error(e, "치수 비교")


@router.get(
    "/drawings/versions/{part_number}",
    response_model=VersionResponse,
)
async def get_versions(part_number: str, pipeline=Depends(get_pipeline)):
    """특정 부품번호의 버전 이력을 반환한다."""
    try:
        versions = pipeline.get_versions(part_number)
        return VersionResponse(
            part_number=part_number,
            versions=[DrawingRecordResponse.from_record(r) for r in versions],
        )
    except Exception as e:
        raise safe_error(e, "버전 이력 조회")


@router.get(
    "/drawings/{drawing_id}/bom",
    response_model=BOMResponse,
)
async def extract_bom(
    drawing_id: str,
    use_llm: bool = Query(False, description="LLM 폴백 사용 여부"),
    pipeline=Depends(get_pipeline),
):
    """도면에서 BOM을 추출한다."""
    record = pipeline.get_record(drawing_id)
    if record is None:
        raise HTTPException(status_code=404, detail="도면을 찾을 수 없습니다.")
    try:
        result = pipeline.extract_bom(drawing_id, use_llm=use_llm)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        entries = [
            BOMEntryResponse(**e) for e in result.get("entries", [])
        ]
        return BOMResponse(
            entries=entries,
            confidence=result.get("confidence", 0.0),
            source=result.get("source", ""),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise safe_error(e, "BOM 추출")


@router.post(
    "/drawings/diff/dxf",
    response_model=DXFDiffResponse,
)
async def diff_dxf(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
    pipeline=Depends(get_pipeline),
):
    """두 DXF 파일을 비교한다."""
    validate_file_extension(file_a.filename, ALLOWED_DXF_EXTENSIONS)
    validate_file_extension(file_b.filename, ALLOWED_DXF_EXTENSIONS)
    tmp_a = save_upload(file_a, suffix=".dxf")
    tmp_b = save_upload(file_b, suffix=".dxf")
    try:
        validate_magic_bytes(tmp_a, ".dxf")
        validate_magic_bytes(tmp_b, ".dxf")
        result = pipeline.compare_dxf(str(tmp_a), str(tmp_b))
        return DXFDiffResponse(
            matched_count=result.get("matched_count", 0),
            only_in_a_count=result.get("only_in_a_count", 0),
            only_in_b_count=result.get("only_in_b_count", 0),
            layer_diff=result.get("layer_diff", {}),
            summary=result.get("summary", {}),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise safe_error(e, "DXF 비교")
    finally:
        tmp_a.unlink(missing_ok=True)
        tmp_b.unlink(missing_ok=True)


@router.get("/tools/versions", response_model=VersionHistoryResponse)
async def get_version_history(pipeline=Depends(get_pipeline)):
    """전체 부품번호별 버전 수를 반환한다."""
    try:
        history = pipeline.get_version_history()
        return VersionHistoryResponse(
            versions=history,
            total_parts=len(history),
        )
    except Exception as e:
        raise safe_error(e, "버전 이력 조회")
