"""
CAD Vision API — LLM 분석 라우터.

도면 설명, Q&A, YOLO 분류, SSE 스트리밍 분석.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_pipeline
from app.api.schemas import AskRequest, AskResponse, ClassifyResponse, DescribeResponse
from app.api.utils import (
    ALLOWED_EXTENSIONS,
    ALLOWED_IMAGE_EXTENSIONS,
    safe_error,
    save_upload,
    validate_file_extension,
    validate_magic_bytes,
)

router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.post(
    "/drawings/{drawing_id}/describe",
    response_model=DescribeResponse,
)
async def describe_drawing(drawing_id: str, pipeline=Depends(get_pipeline)):
    """LLM으로 도면을 분석/설명한다."""
    record = pipeline.get_record(drawing_id)
    if record is None:
        raise HTTPException(status_code=404, detail="도면을 찾을 수 없습니다.")
    try:
        desc = pipeline.describe(
            image_path=record.file_path, drawing_id=drawing_id,
        )
        return DescribeResponse(drawing_id=drawing_id, description=desc)
    except Exception as e:
        raise safe_error(e, "도면 분석")


@router.post(
    "/drawings/{drawing_id}/ask",
    response_model=AskResponse,
)
async def ask_drawing(drawing_id: str, req: AskRequest, pipeline=Depends(get_pipeline)):
    """도면에 대해 질문한다."""
    record = pipeline.get_record(drawing_id)
    if record is None:
        raise HTTPException(status_code=404, detail="도면을 찾을 수 없습니다.")
    try:
        answer = pipeline.ask(
            image_path=record.file_path,
            question=req.question,
            drawing_id=drawing_id,
        )
        return AskResponse(
            drawing_id=drawing_id, question=req.question, answer=answer,
        )
    except Exception as e:
        raise safe_error(e, "도면 Q&A")


# ── YOLO 분류 ──


@router.post("/drawings/classify", response_model=ClassifyResponse)
async def classify_drawing(
    file: UploadFile = File(...),
    pipeline=Depends(get_pipeline),
):
    """도면을 YOLO로 분류한다. CAD 포맷(STP/IGES/DWG/STL)은 자동 PNG 변환."""
    ext = validate_file_extension(file.filename, ALLOWED_EXTENSIONS)
    tmp_path = save_upload(file)
    try:
        validate_magic_bytes(tmp_path, ext)
        # CAD 포맷 → PNG 변환
        classify_path = str(tmp_path)
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            from core.cad_router import ensure_processable
            cad_result = ensure_processable(str(tmp_path))
            if cad_result.status in ("ready", "converted") and cad_result.png_path:
                classify_path = cad_result.png_path
            else:
                raise HTTPException(400, detail=cad_result.guidance or "CAD 변환 실패")
        result = pipeline.classify_with_detail(classify_path)
        if result is None:
            return ClassifyResponse()
        return ClassifyResponse(
            category=getattr(result, "category", ""),
            confidence=getattr(result, "confidence", 0.0),
            needs_review=getattr(result, "needs_review", False),
            top_k=[
                {"category": c, "confidence": s}
                for c, s in getattr(result, "top_k", [])
            ],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise safe_error(e, "도면 분류")
    finally:
        tmp_path.unlink(missing_ok=True)


# ── SSE 스트리밍 분석 ──


@router.post("/drawings/analyze/stream")
async def analyze_stream(
    file: UploadFile = File(...),
    question: str = Query("이 도면을 분석해주세요.", max_length=2000),
    num_predict: int = Query(2048, ge=100, le=8192),
    pipeline=Depends(get_pipeline),
):
    """LLM 스트리밍 분석. SSE (text/event-stream)로 토큰을 전달한다. CAD 포맷 자동 변환."""
    ext = validate_file_extension(file.filename, ALLOWED_EXTENSIONS)
    tmp_path = save_upload(file)
    try:
        validate_magic_bytes(tmp_path, ext)
    except HTTPException:
        tmp_path.unlink(missing_ok=True)
        raise

    # CAD 포맷 → PNG 변환
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        from core.cad_router import ensure_processable
        cad_result = ensure_processable(str(tmp_path))
        if cad_result.status in ("ready", "converted") and cad_result.png_path:
            from pathlib import Path as _P
            tmp_path = _P(cad_result.png_path)
        else:
            tmp_path.unlink(missing_ok=True)
            raise HTTPException(400, detail=cad_result.guidance or "CAD 변환 실패")

    def _stream_generator():
        try:
            llm = pipeline._llm
            for token in llm._generate_stream(question, str(tmp_path), num_predict):
                data = json.dumps({"token": token}, ensure_ascii=False)
                yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
        finally:
            tmp_path.unlink(missing_ok=True)

    return StreamingResponse(
        _stream_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
