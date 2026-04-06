"""
CAD Vision API — 도면 라우터.

등록, 검색 (텍스트/이미지/DXF), 조회, 목록, 삭제.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.api.dependencies import get_pipeline
from app.api.schemas import (
    DrawingRecordResponse,
    PaginatedResponse,
    PartNumberSearchRequest,
    SearchResultResponse,
    TextSearchRequest,
    UnifiedSearchRequest,
    UnifiedSearchResultResponse,
)
from app.api.utils import (
    ALLOWED_DXF_EXTENSIONS,
    ALLOWED_EXTENSIONS,
    ALLOWED_IMAGE_EXTENSIONS,
    safe_error,
    save_upload,
    validate_file_extension,
    validate_magic_bytes,
)

router = APIRouter(prefix="/api/v1", tags=["drawings"])


# ── 도면 등록 ──


@router.post("/drawings/register", response_model=DrawingRecordResponse)
async def register_drawing(
    file: UploadFile = File(...),
    category: str = Query("", description="카테고리 지정 (빈 문자열이면 YOLO 자동 분류)"),
    use_llm: bool = Query(False, description="LLM 메타데이터 생성 여부"),
    pipeline=Depends(get_pipeline),
):
    """도면을 등록한다. PNG/JPG/TIFF/DXF 지원."""
    ext = validate_file_extension(file.filename, ALLOWED_EXTENSIONS)
    tmp_path = save_upload(file)
    try:
        validate_magic_bytes(tmp_path, ext)
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
        raise safe_error(e, "도면 등록")
    finally:
        tmp_path.unlink(missing_ok=True)


# ── 검색 ──


@router.post(
    "/drawings/search/text",
    response_model=list[SearchResultResponse],
)
async def search_by_text(req: TextSearchRequest, pipeline=Depends(get_pipeline)):
    """자연어 텍스트로 도면을 검색한다."""
    try:
        results = pipeline.search_by_text(
            query=req.query, top_k=req.top_k, category=req.category,
        )
        return [SearchResultResponse.from_result(r) for r in results]
    except Exception as e:
        raise safe_error(e, "텍스트 검색")


@router.post(
    "/drawings/search/image",
    response_model=list[SearchResultResponse],
)
async def search_by_image(
    file: UploadFile = File(...),
    top_k: int = Query(5, ge=1, le=100),
    category: str = Query(""),
    pipeline=Depends(get_pipeline),
):
    """이미지로 유사 도면을 검색한다."""
    ext = validate_file_extension(file.filename, ALLOWED_IMAGE_EXTENSIONS)
    tmp_path = save_upload(file)
    try:
        validate_magic_bytes(tmp_path, ext)
        results = pipeline.search_by_image(
            image_path=tmp_path, top_k=top_k, category=category,
        )
        return [SearchResultResponse.from_result(r) for r in results]
    except HTTPException:
        raise
    except Exception as e:
        raise safe_error(e, "이미지 검색")
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post(
    "/drawings/search/dxf",
    response_model=list[SearchResultResponse],
)
async def search_by_dxf(
    file: UploadFile = File(...),
    top_k: int = Query(5, ge=1, le=100),
    category: str = Query(""),
    pipeline=Depends(get_pipeline),
):
    """DXF 구조로 유사 도면을 검색한다 (GNN)."""
    validate_file_extension(file.filename, ALLOWED_DXF_EXTENSIONS)
    tmp_path = save_upload(file, suffix=".dxf")
    try:
        validate_magic_bytes(tmp_path, ".dxf")
        results = pipeline.search_by_dxf(
            dxf_path=tmp_path, top_k=top_k, category=category,
        )
        return [SearchResultResponse.from_result(r) for r in results]
    except HTTPException:
        raise
    except Exception as e:
        raise safe_error(e, "DXF 검색")
    finally:
        tmp_path.unlink(missing_ok=True)


# ── 도면 조회/삭제 ──


@router.get("/drawings/{drawing_id}", response_model=DrawingRecordResponse)
async def get_drawing(drawing_id: str, pipeline=Depends(get_pipeline)):
    """도면 레코드를 조회한다."""
    record = pipeline.get_record(drawing_id)
    if record is None:
        raise HTTPException(status_code=404, detail="도면을 찾을 수 없습니다.")
    return DrawingRecordResponse.from_record(record)


@router.get("/drawings", response_model=PaginatedResponse)
async def list_drawings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str = Query("", description="카테고리 필터"),
    material: str = Query("", description="재질 필터"),
    search: str = Query("", description="파일명/부품번호 검색"),
    pipeline=Depends(get_pipeline),
):
    """등록된 도면 목록을 페이지네이션 + 필터로 반환한다."""
    all_records = pipeline.get_all_records()

    # 필터 적용
    if category:
        all_records = [r for r in all_records if getattr(r, "category", "") == category]
    if material:
        mat_upper = material.upper()
        all_records = [
            r for r in all_records
            if any(mat_upper in m.upper() for m in (getattr(r, "materials", []) or []))
        ]
    if search:
        q = search.upper()
        all_records = [
            r for r in all_records
            if q in (getattr(r, "file_name", "") or "").upper()
            or any(q in pn.upper() for pn in (getattr(r, "part_numbers", []) or []))
        ]

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


@router.post(
    "/drawings/search/part-number",
    response_model=list[DrawingRecordResponse],
)
async def search_by_part_number(req: PartNumberSearchRequest, pipeline=Depends(get_pipeline)):
    """부품번호로 도면을 검색한다."""
    try:
        records = pipeline.search_by_part_number(req.part_number)
        return [DrawingRecordResponse.from_record(r) for r in records]
    except Exception as e:
        raise safe_error(e, "부품번호 검색")


@router.delete("/drawings/{drawing_id}")
async def delete_drawing(drawing_id: str, pipeline=Depends(get_pipeline)):
    """도면을 삭제한다."""
    success = pipeline.delete_drawing(drawing_id)
    if not success:
        raise HTTPException(status_code=404, detail="도면을 찾을 수 없습니다.")
    return {"status": "deleted", "drawing_id": drawing_id}


# ── v5.4 통합 검색 ──


@router.post(
    "/drawings/search/unified",
    response_model=list[UnifiedSearchResultResponse],
)
async def unified_search(req: UnifiedSearchRequest, pipeline=Depends(get_pipeline)):
    """통합 검색 (v5.4) — 텍스트/이미지/GNN/부품번호 채널 조합 가능."""
    from core.models import SearchChannel, SearchQuery

    try:
        channels = []
        for ch_name in req.channels:
            try:
                channels.append(SearchChannel(ch_name))
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"유효하지 않은 검색 채널: {ch_name}. "
                           f"가능한 값: text, image, gnn, part_number",
                )

        query = SearchQuery(
            text=req.text or None,
            part_number=req.part_number or None,
            channels=channels,
            top_k=req.top_k,
            filters={"category": req.category} if req.category else {},
        )

        results = pipeline.search_engine.search(query)
        return [UnifiedSearchResultResponse.from_unified(r) for r in results]
    except HTTPException:
        raise
    except Exception as e:
        raise safe_error(e, "통합 검색")


# ── v5.4 React 프론트엔드용 파일 서빙 ──


@router.get("/drawings/{drawing_id}/image")
async def get_drawing_image(drawing_id: str, pipeline=Depends(get_pipeline)):
    """도면 이미지 파일을 반환한다 (PNG/JPG). DXF는 자동 PNG 변환."""
    record = pipeline.get_record(drawing_id)
    if record is None:
        raise HTTPException(status_code=404, detail="도면을 찾을 수 없습니다.")

    file_path = _find_image_file(record)
    if file_path is None:
        raise HTTPException(status_code=404, detail="이미지 파일을 찾을 수 없습니다.")

    media = "image/png" if file_path.suffix.lower() == ".png" else "image/jpeg"
    return FileResponse(str(file_path), media_type=media)


@router.get("/drawings/{drawing_id}/thumbnail")
async def get_drawing_thumbnail(drawing_id: str, pipeline=Depends(get_pipeline)):
    """도면 썸네일을 반환한다 (256px 캐시)."""
    record = pipeline.get_record(drawing_id)
    if record is None:
        raise HTTPException(status_code=404, detail="도면을 찾을 수 없습니다.")

    # 리맵된 경로로 썸네일 생성
    remapped = _remap_path(record.file_path)
    try:
        thumb_path = pipeline.renderer.render_thumbnail(str(remapped))
        if thumb_path and Path(thumb_path).exists():
            return FileResponse(thumb_path, media_type="image/png")
    except Exception:
        pass

    # 폴백: 원본 이미지
    file_path = _find_image_file(record)
    if file_path:
        return FileResponse(str(file_path), media_type="image/png")

    raise HTTPException(status_code=404, detail="썸네일을 생성할 수 없습니다.")


@router.post("/drawings/register-batch")
async def register_batch(
    files: list[UploadFile] = File(...),
    category: str = Query("", description="카테고리 (빈 문자열이면 YOLO 자동)"),
    pipeline=Depends(get_pipeline),
):
    """여러 도면을 한번에 등록한다."""
    from core.cad_router import ensure_processable

    results = []
    for file in files:
        tmp_path = save_upload(file)
        try:
            ext = Path(file.filename or "").suffix.lower()
            # CAD Router로 포맷 변환
            cad_result = ensure_processable(str(tmp_path))
            if cad_result.status == "unsupported":
                results.append({
                    "status": "skipped",
                    "file": file.filename,
                    "reason": cad_result.guidance or "미지원 포맷",
                })
                continue

            reg_path = Path(cad_result.png_path) if cad_result.png_path else tmp_path
            record = pipeline.register_drawing(
                image_path=reg_path, category=category,
                use_llm=False, copy_to_store=True,
            )
            results.append({
                "status": "ok",
                "file": file.filename,
                "drawing_id": record.drawing_id,
                "category": record.category,
            })
        except Exception as e:
            results.append({
                "status": "error",
                "file": file.filename,
                "error": str(e),
            })
        finally:
            tmp_path.unlink(missing_ok=True)

    success = sum(1 for r in results if r["status"] == "ok")
    return {
        "total": len(files),
        "success": success,
        "failed": len(files) - success,
        "results": results,
    }


# ── 내부 헬퍼 ──


def _remap_path(file_path: str) -> Path:
    """DB에 저장된 경로를 현재 환경의 실제 경로로 리맵한다."""
    from config.settings import settings

    p = Path(file_path)
    if p.exists():
        return p

    # settings.py의 경로 리맵 적용
    remap_from = settings.drawing_path_remap_from
    remap_to = settings.drawing_path_remap_to
    if remap_from and remap_to and file_path.startswith(remap_from):
        remapped = Path(file_path.replace(remap_from, remap_to, 1))
        if remapped.exists():
            return remapped

    return p


def _find_image_file(record) -> Path | None:
    """레코드에서 표시 가능한 이미지 파일 경로를 찾는다."""
    import hashlib
    import tempfile

    raw_path = getattr(record, "file_path", "")
    if not raw_path:
        return None

    # 1) file_path (리맵 포함)
    fp = _remap_path(raw_path)
    if fp.exists() and fp.suffix.lower() in {".png", ".jpg", ".jpeg"}:
        return fp

    # 2) DXF → PNG 렌더링
    if fp.exists() and fp.suffix.lower() == ".dxf":
        try:
            from core.dxf_renderer import DXFRenderer
            renderer = DXFRenderer(dpi=100, figsize=(6, 6))
            name_hash = hashlib.md5(str(fp).encode()).hexdigest()[:12]
            tmp_dir = Path(tempfile.gettempdir()) / "drawingllm_api_thumbs"
            tmp_dir.mkdir(exist_ok=True)
            png_path = tmp_dir / f"{name_hash}.png"
            if png_path.exists():
                return png_path
            renderer.render_to_png(fp, png_path)
            return png_path
        except Exception:
            pass

    # 3) dxf_path 연결 (리맵 포함)
    dxf_p = getattr(record, "dxf_path", "")
    if dxf_p:
        dp = _remap_path(dxf_p)
        if dp.exists() and dp.suffix.lower() == ".dxf":
            try:
                from core.dxf_renderer import DXFRenderer
                renderer = DXFRenderer(dpi=100, figsize=(6, 6))
                name_hash = hashlib.md5(str(dp).encode()).hexdigest()[:12]
                tmp_dir = Path(tempfile.gettempdir()) / "drawingllm_api_thumbs"
                tmp_dir.mkdir(exist_ok=True)
                png_path = tmp_dir / f"{name_hash}.png"
                if png_path.exists():
                    return png_path
                renderer.render_to_png(dp, png_path)
                return png_path
            except Exception:
                pass

    return None
