"""
CAD Vision API — 공용 유틸리티.

파일 검증, 업로드 저장, 에러 응답 등 라우터 간 공유 함수.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import HTTPException, UploadFile
from loguru import logger

from config.settings import settings

# ── 허용 파일 확장자 + Magic bytes ──

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".pdf"}
ALLOWED_DXF_EXTENSIONS = {".dxf"}
ALLOWED_CAD_EXTENSIONS = {".dwg", ".stp", ".step", ".igs", ".iges", ".stl"}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DXF_EXTENSIONS | ALLOWED_CAD_EXTENSIONS

# 파일 헤더 시그니처 (magic bytes)
MAGIC_BYTES = {
    b"\x89PNG": ".png",
    b"\xff\xd8\xff": ".jpg",
    b"II\x2a\x00": ".tiff",  # little-endian TIFF
    b"MM\x00\x2a": ".tiff",  # big-endian TIFF
    b"%PDF": ".pdf",
}

MAX_FILE_SIZE_BYTES = settings.max_file_size_mb * 1024 * 1024


def validate_file_extension(filename: str | None, allowed: set[str]) -> str:
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


def validate_magic_bytes(file_path: Path, ext: str) -> None:
    """파일 헤더(magic bytes)로 실제 파일 형식 검증. DXF/CAD 바이너리는 스킵."""
    # CAD 바이너리 형식은 magic bytes 검증 불필요
    if ext in ALLOWED_CAD_EXTENSIONS:
        return
    if ext in ALLOWED_DXF_EXTENSIONS:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                first_line = f.readline(100).strip()
            if first_line and not first_line[0].isdigit():
                raise HTTPException(
                    status_code=400,
                    detail="유효한 DXF 파일이 아닙니다.",
                )
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="유효한 DXF 파일이 아닙니다.")
        return

    try:
        with open(file_path, "rb") as f:
            header = f.read(8)
    except OSError:
        raise HTTPException(status_code=400, detail="파일을 읽을 수 없습니다.")

    for magic, expected_ext in MAGIC_BYTES.items():
        if header.startswith(magic):
            return
    logger.warning(f"Magic bytes 불일치: ext={ext}, header={header[:4].hex()}")


def save_upload(upload: UploadFile, suffix: str = "", max_size: int = 0) -> Path:
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


def safe_error(e: Exception, context: str = "") -> HTTPException:
    """보안: 내부 에러 메시지를 클라이언트에 노출하지 않음."""
    logger.error(f"{context}: {type(e).__name__}: {e}")
    return HTTPException(status_code=500, detail=f"{context} 처리 중 오류가 발생했습니다.")
