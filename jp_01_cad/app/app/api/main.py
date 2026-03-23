"""
CAD Vision REST API — FastAPI 애플리케이션.

DrawingPipeline의 모든 기능을 REST 엔드포인트로 노출한다.
Streamlit과 동일한 Pipeline 싱글톤을 공유한다.

실행:
    uvicorn app.api.main:app --host 0.0.0.0 --port 8000
    또는: python run_api.py
"""

from __future__ import annotations

import shutil
import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.schemas import (
    AskRequest,
    AskResponse,
    BOMResponse,
    BOMEntryResponse,
    DescribeResponse,
    DimensionCompareRequest,
    DimensionCompareResponse,
    DrawingRecordResponse,
    DXFDiffResponse,
    PaginatedResponse,
    SearchResultResponse,
    StatsResponse,
    TextSearchRequest,
    VersionResponse,
)
from config.settings import settings
from core.dependencies import get_pipeline

# ── 허용 파일 확장자 + Magic bytes ──

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".pdf"}
ALLOWED_DXF_EXTENSIONS = {".dxf"}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DXF_EXTENSIONS

# 파일 헤더 시그니처 (magic bytes)
MAGIC_BYTES = {
    b"\x89PNG": ".png",
    b"\xff\xd8\xff": ".jpg",
    b"II\x2a\x00": ".tiff",  # little-endian TIFF
    b"MM\x00\x2a": ".tiff",  # big-endian TIFF
    b"%PDF": ".pdf",
}

MAX_FILE_SIZE_BYTES = settings.max_file_size_mb * 1024 * 1024

# ── Rate Limiter (in-memory, IP 기반) ──

_rate_limit_store: dict[str, list[float]] = {}
API_RATE_LIMIT_RPM = 60  # 분당 최대 요청 수


def _check_rate_limit(client_ip: str) -> bool:
    """IP 기반 간단한 rate limiting. True면 허용, False면 차단."""
    now = time.time()
    window = 60.0  # 1분

    if client_ip not in _rate_limit_store:
        _rate_limit_store[client_ip] = []

    # 1분 이전 기록 제거
    _rate_limit_store[client_ip] = [
        t for t in _rate_limit_store[client_ip] if now - t < window
    ]

    if len(_rate_limit_store[client_ip]) >= API_RATE_LIMIT_RPM:
        return False

    _rate_limit_store[client_ip].append(now)
    return True


# ── FastAPI 앱 ──

app = FastAPI(
    title="CAD Vision API",
    description="AI 기반 산업 도면 검색 및 분류 시스템",
    version="4.0",
)

# 🔴 보안 수정: CORS — credentials=False, 특정 origins 권장
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:3000"],  # Streamlit + dev
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


# ── Rate Limit 미들웨어 ──


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """IP 기반 Rate Limiting."""
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        return _json_error(429, "요청이 너무 많습니다. 잠시 후 다시 시도하세요.")
    return await call_next(request)


def _json_error(status_code: int, message: str):
    """안전한 JSON 에러 응답 (내부 정보 노출 방지)."""
    from starlette.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={"detail": message},
    )


# ── 유틸리티 ──


def _validate_file_extension(filename: str | None, allowed: set[str]) -> str:
    """파일 확장자 검증. 유효하면 확장자 반환, 아니면 HTTPException."""
    if not filename:
        raise HTTPException(status_code=400, detail="파일명이 없습니다.")
    ext = Path(filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다. (허용: {', '.join(sorted(allowed))})",
        )
    return ext


def _validate_magic_bytes(file_path: Path, ext: str) -> None:
    """파일 헤더(magic bytes)로 실제 파일 형식 검증. DXF는 텍스트라 스킵."""
    if ext in ALLOWED_DXF_EXTENSIONS:
        # DXF는 텍스트 파일이라 magic bytes 대신 첫 줄 검증
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                first_line = f.readline(100).strip()
            # DXF는 보통 "0" 또는 숫자로 시작
            if first_line and not first_line[0].isdigit():
                raise HTTPException(
                    status_code=400,
                    detail="유효한 DXF 파일이 아닙니다.",
                )
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="유효한 DXF 파일이 아닙니다.")
        return

    # 바이너리 파일: magic bytes 검증
    try:
        with open(file_path, "rb") as f:
            header = f.read(8)
    except OSError:
        raise HTTPException(status_code=400, detail="파일을 읽을 수 없습니다.")

    for magic, expected_ext in MAGIC_BYTES.items():
        if header.startswith(magic):
            return  # 유효
    # magic bytes 불일치 → 경고 로그만 (일부 정상 파일도 불일치 가능)
    logger.warning(f"Magic bytes 불일치: ext={ext}, header={header[:4].hex()}")


def _save_upload(upload: UploadFile, suffix: str = "", max_size: int = 0) -> Path:
    """UploadFile을 임시 파일로 저장. 크기 제한 적용."""
    if not suffix:
        suffix = Path(upload.filename or "file").suffix
    max_size = max_size or MAX_FILE_SIZE_BYTES

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        total = 0
        chunk_size = 1024 * 1024  # 1MB
        while True:
            chunk = upload.file.read(chunk_size)
            if not chunk:
                break
            total += len(chunk)
            if total > max_size:
                tmp.close()
                Path(tmp.name).unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"파일이 너무 큽니다. (최대 {max_size // (1024*1024)}MB)",
                )
            tmp.write(chunk)
        tmp.close()
    except HTTPException:
        raise
    except Exception:
        tmp.close()
        Path(tmp.name).unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="파일 업로드 실패")

    return Path(tmp.name)


def _safe_error(e: Exception, context: str = "") -> HTTPException:
    """🔴 보안: 내부 에러 메시지를 클라이언트에 노출하지 않음."""
    logger.error(f"{context}: {type(e).__name__}: {e}")
    return HTTPException(status_code=500, detail=f"{context} 처리 중 오류가 발생했습니다.")


# ── 도면 등록 ──


@app.post("/api/v1/drawings/register", response_model=DrawingRecordResponse)
async def register_drawing(
    file: UploadFile = File(...),
    category: str = Query("", description="카테고리 지정 (빈 문자열이면 YOLO 자동 분류)"),
    use_llm: bool = Query(False, description="LLM 메타데이터 생성 여부"),
):
    """도면을 등록한다. PNG/JPG/TIFF/DXF 지원."""
    ext = _validate_file_extension(file.filename, ALLOWED_EXTENSIONS)
    tmp_path = _save_upload(file)
    try:
        _validate_magic_bytes(tmp_path, ext)
        pipeline = get_pipeline()
        record = pipeline.register_drawing(
            image_path=tmp_path,
            category=category,
            use_llm=use_llm,
            copy_to_store=True,
        )
        return DrawingRecordResponse.from_record(record)
    except HTTPException:
        raise
    except Exception as e:
        raise _safe_error(e, "도면 등록")
    finally:
        tmp_path.unlink(missing_ok=True)


# ── 검색 ──


@app.post(
    "/api/v1/drawings/search/text",
    response_model=list[SearchResultResponse],
)
async def search_by_text(req: TextSearchRequest):
    """자연어 텍스트로 도면을 검색한다."""
    try:
        pipeline = get_pipeline()
        results = pipeline.search_by_text(
            query=req.query, top_k=req.top_k, category=req.category,
        )
        return [SearchResultResponse.from_result(r) for r in results]
    except Exception as e:
        raise _safe_error(e, "텍스트 검색")


@app.post(
    "/api/v1/drawings/search/image",
    response_model=list[SearchResultResponse],
)
async def search_by_image(
    file: UploadFile = File(...),
    top_k: int = Query(5, ge=1, le=100),
    category: str = Query(""),
):
    """이미지로 유사 도면을 검색한다."""
    ext = _validate_file_extension(file.filename, ALLOWED_IMAGE_EXTENSIONS)
    tmp_path = _save_upload(file)
    try:
        _validate_magic_bytes(tmp_path, ext)
        pipeline = get_pipeline()
        results = pipeline.search_by_image(
            image_path=tmp_path, top_k=top_k, category=category,
        )
        return [SearchResultResponse.from_result(r) for r in results]
    except HTTPException:
        raise
    except Exception as e:
        raise _safe_error(e, "이미지 검색")
    finally:
        tmp_path.unlink(missing_ok=True)


@app.post(
    "/api/v1/drawings/search/dxf",
    response_model=list[SearchResultResponse],
)
async def search_by_dxf(
    file: UploadFile = File(...),
    top_k: int = Query(5, ge=1, le=100),
    category: str = Query(""),
):
    """DXF 구조로 유사 도면을 검색한다 (GNN)."""
    _validate_file_extension(file.filename, ALLOWED_DXF_EXTENSIONS)
    tmp_path = _save_upload(file, suffix=".dxf")
    try:
        _validate_magic_bytes(tmp_path, ".dxf")
        pipeline = get_pipeline()
        results = pipeline.search_by_dxf(
            dxf_path=tmp_path, top_k=top_k, category=category,
        )
        return [SearchResultResponse.from_result(r) for r in results]
    except HTTPException:
        raise
    except Exception as e:
        raise _safe_error(e, "DXF 검색")
    finally:
        tmp_path.unlink(missing_ok=True)


# ── 도면 조회/삭제 ──


@app.get("/api/v1/drawings/{drawing_id}", response_model=DrawingRecordResponse)
async def get_drawing(drawing_id: str):
    """도면 레코드를 조회한다."""
    pipeline = get_pipeline()
    record = pipeline.get_record(drawing_id)
    if record is None:
        raise HTTPException(status_code=404, detail="도면을 찾을 수 없습니다.")
    return DrawingRecordResponse.from_record(record)


@app.get("/api/v1/drawings", response_model=PaginatedResponse)
async def list_drawings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """등록된 도면 목록을 페이지네이션으로 반환한다."""
    pipeline = get_pipeline()
    all_records = pipeline.get_all_records()
    total = len(all_records)
    start = (page - 1) * page_size
    end = start + page_size
    items = [
        DrawingRecordResponse.from_record(r)
        for r in all_records[start:end]
    ]
    return PaginatedResponse(
        items=items, total=total, page=page, page_size=page_size,
    )


@app.delete("/api/v1/drawings/{drawing_id}")
async def delete_drawing(drawing_id: str):
    """도면을 삭제한다."""
    pipeline = get_pipeline()
    success = pipeline.delete_drawing(drawing_id)
    if not success:
        raise HTTPException(status_code=404, detail="도면을 찾을 수 없습니다.")
    return {"status": "deleted", "drawing_id": drawing_id}


# ── LLM 분석 ──


@app.post(
    "/api/v1/drawings/{drawing_id}/describe",
    response_model=DescribeResponse,
)
async def describe_drawing(drawing_id: str):
    """LLM으로 도면을 분석/설명한다."""
    pipeline = get_pipeline()
    record = pipeline.get_record(drawing_id)
    if record is None:
        raise HTTPException(status_code=404, detail="도면을 찾을 수 없습니다.")
    try:
        desc = pipeline.describe(
            image_path=record.file_path, drawing_id=drawing_id,
        )
        return DescribeResponse(drawing_id=drawing_id, description=desc)
    except Exception as e:
        raise _safe_error(e, "도면 분석")


@app.post(
    "/api/v1/drawings/{drawing_id}/ask",
    response_model=AskResponse,
)
async def ask_drawing(drawing_id: str, req: AskRequest):
    """도면에 대해 질문한다."""
    pipeline = get_pipeline()
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
        raise _safe_error(e, "도면 Q&A")


# ── 통계 ──


@app.get("/api/v1/stats", response_model=StatsResponse)
async def get_stats():
    """시스템 통계를 반환한다."""
    try:
        pipeline = get_pipeline()
        stats = pipeline.get_stats()
        vs = stats.get("vector_store", {})
        yolo_cls = stats.get("yolo_classifier", {})
        yolo_det = stats.get("yolo_detector", {})
        gnn = stats.get("gnn_embedder", {})
        return StatsResponse(
            total_drawings=stats.get("total_drawings", 0),
            image_collection_count=vs.get("image_collection_count", 0),
            text_collection_count=vs.get("text_collection_count", 0),
            gnn_collection_count=vs.get("gnn_collection_count", 0),
            categories=stats.get("categories", []),
            ollama_status="healthy" if stats.get("ollama_healthy") else "unavailable",
            yolo_cls_enabled=yolo_cls.get("enabled", False),
            yolo_det_enabled=yolo_det.get("enabled", False),
            gnn_enabled=gnn.get("enabled", False),
        )
    except Exception as e:
        raise _safe_error(e, "통계 조회")


# ── Tier-3: 치수 비교 / 버전 이력 / BOM 추출 / DXF 비교 ──


@app.post(
    "/api/v1/drawings/compare/dimensions",
    response_model=DimensionCompareResponse,
)
async def compare_dimensions(req: DimensionCompareRequest):
    """두 도면의 치수를 비교한다."""
    try:
        pipeline = get_pipeline()
        result = pipeline.compare_dimensions(req.drawing_id_1, req.drawing_id_2)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return DimensionCompareResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise _safe_error(e, "치수 비교")


@app.get(
    "/api/v1/drawings/versions/{part_number}",
    response_model=VersionResponse,
)
async def get_versions(part_number: str):
    """특정 부품번호의 버전 이력을 반환한다."""
    try:
        pipeline = get_pipeline()
        versions = pipeline.get_versions(part_number)
        return VersionResponse(
            part_number=part_number,
            versions=[DrawingRecordResponse.from_record(r) for r in versions],
        )
    except Exception as e:
        raise _safe_error(e, "버전 이력 조회")


@app.get(
    "/api/v1/drawings/{drawing_id}/bom",
    response_model=BOMResponse,
)
async def extract_bom(
    drawing_id: str,
    use_llm: bool = Query(False, description="LLM 폴백 사용 여부"),
):
    """도면에서 BOM을 추출한다."""
    pipeline = get_pipeline()
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
        raise _safe_error(e, "BOM 추출")


@app.post(
    "/api/v1/drawings/diff/dxf",
    response_model=DXFDiffResponse,
)
async def diff_dxf(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
):
    """두 DXF 파일을 비교한다."""
    _validate_file_extension(file_a.filename, ALLOWED_DXF_EXTENSIONS)
    _validate_file_extension(file_b.filename, ALLOWED_DXF_EXTENSIONS)
    tmp_a = _save_upload(file_a, suffix=".dxf")
    tmp_b = _save_upload(file_b, suffix=".dxf")
    try:
        _validate_magic_bytes(tmp_a, ".dxf")
        _validate_magic_bytes(tmp_b, ".dxf")
        pipeline = get_pipeline()
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
        raise _safe_error(e, "DXF 비교")
    finally:
        tmp_a.unlink(missing_ok=True)
        tmp_b.unlink(missing_ok=True)


# ── Tier-4: 피드백 ──

_feedback_store = None


def _get_feedback_store():
    """FeedbackStore 싱글톤 (lazy init)."""
    global _feedback_store
    if _feedback_store is None:
        from core.feedback_store import FeedbackStore
        _feedback_store = FeedbackStore()
    return _feedback_store


@app.post("/api/v1/feedback")
async def submit_feedback(
    query_text: str = Query(...),
    query_type: str = Query("text"),
    drawing_id: str = Query(...),
    score: float = Query(0.0),
    relevance: int = Query(..., ge=-1, le=1),
    category: str = Query(""),
    comment: str = Query(""),
):
    """검색 결과에 대한 피드백을 제출한다."""
    try:
        store = _get_feedback_store()
        feedback_id = store.add_feedback(
            query_text=query_text,
            query_type=query_type,
            drawing_id=drawing_id,
            score=score,
            relevance=relevance,
            category=category,
            comment=comment,
        )
        return {"status": "ok", "feedback_id": feedback_id}
    except Exception as e:
        raise _safe_error(e, "피드백 제출")


@app.get("/api/v1/feedback/stats")
async def get_feedback_stats():
    """피드백 통계를 반환한다."""
    try:
        store = _get_feedback_store()
        return store.get_feedback_stats()
    except Exception as e:
        raise _safe_error(e, "피드백 통계 조회")


@app.post("/api/v1/feedback/export")
async def export_feedback(format: str = Query("jsonl")):
    """피드백을 학습 데이터로 내보낸다.

    format: "jsonl" (학습 쌍) 또는 "csv" (전체 피드백)
    """
    try:
        store = _get_feedback_store()
        if format == "csv":
            path = store.export_csv()
        else:
            path = store.export_training_pairs()
        return {"status": "ok", "format": format, "path": path}
    except Exception as e:
        raise _safe_error(e, "피드백 내보내기")
