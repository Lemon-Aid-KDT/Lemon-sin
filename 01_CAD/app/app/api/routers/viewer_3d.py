"""
CAD Vision API — 3D 뷰어 라우터.

STL/STEP/IGES → Three.js 호환 메시 데이터 + 메타데이터 제공.
"""

from __future__ import annotations

from pathlib import Path as _Path

from pydantic import BaseModel, Field
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.api.utils import safe_error, save_upload

router = APIRouter(prefix="/api/v1", tags=["viewer"])

ALLOWED_3D_EXTENSIONS = {".stl", ".stp", ".step", ".igs", ".iges"}


# ── 스키마 ──

class STLBBox(BaseModel):
    """3D 바운딩 박스."""
    min: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    max: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    center: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    size: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])


class STLViewerResponse(BaseModel):
    """3D 뷰어 응답."""
    vertices: list[float] = Field(default_factory=list)
    normals: list[float] = Field(default_factory=list)
    triangle_count: int = 0
    vertex_count: int = 0
    bbox: STLBBox | None = None
    format: str = ""
    file_size_bytes: int = 0


# ── 엔드포인트 ──

@router.post(
    "/viewer/stl",
    response_model=STLViewerResponse,
    summary="3D 파일 → 메시 데이터 (STL/STEP/IGES 지원)",
)
async def parse_3d(file: UploadFile = File(...)):
    """3D 파일을 Three.js 호환 메시 데이터로 변환한다. STEP/IGES는 STL로 자동 변환."""
    ext = _Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_3D_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다. (허용: {', '.join(sorted(ALLOWED_3D_EXTENSIONS))})",
        )

    tmp = save_upload(file, suffix=ext)
    try:
        stl_path = tmp

        # STEP/IGES → STL 변환 (CadQuery 직접 사용)
        if ext in {".stp", ".step", ".igs", ".iges"}:
            import tempfile as _tmpmod
            stl_out = _Path(_tmpmod.gettempdir()) / f"{tmp.stem}_3d.stl"

            try:
                if ext in {".stp", ".step"}:
                    import cadquery as cq
                    shape = cq.importers.importStep(str(tmp))
                    cq.exporters.export(shape, str(stl_out), exportType="STL")
                else:
                    # IGES → OCP → STL
                    from OCP.IGESControl import IGESControl_Reader
                    from OCP.IFSelect import IFSelect_RetDone
                    from OCP.BRepMesh import BRepMesh_IncrementalMesh
                    from OCP.TopExp import TopExp_Explorer
                    from OCP.TopAbs import TopAbs_FACE
                    reader = IGESControl_Reader()
                    if reader.ReadFile(str(tmp)) == IFSelect_RetDone:
                        reader.TransferRoots()
                        ocp_shape = reader.OneShape()

                        # 2D 와이어프레임 체크: FACE가 없으면 STL 변환 불가
                        face_exp = TopExp_Explorer(ocp_shape, TopAbs_FACE)
                        if not face_exp.More():
                            raise HTTPException(
                                400,
                                detail="이 IGES 파일은 2D 와이어프레임(선분만 포함)이므로 "
                                       "3D 메시(STL)로 변환할 수 없습니다. "
                                       "3D 솔리드가 포함된 IGES 파일을 업로드하거나, "
                                       "DXF 뷰어에서 2D 도면으로 확인하세요.",
                            )

                        BRepMesh_IncrementalMesh(ocp_shape, 0.1)
                        try:
                            import cadquery as cq
                            cq_shape = cq.Shape(ocp_shape)
                            cq_shape.exportStl(str(stl_out), tolerance=0.1)
                        except Exception:
                            from OCP.StlAPI import StlAPI_Writer
                            writer = StlAPI_Writer()
                            writer.Write(ocp_shape, str(stl_out))
            except ImportError:
                raise HTTPException(400, detail="CadQuery/OCP가 설치되지 않았습니다.")
            except Exception as conv_err:
                raise HTTPException(400, detail=f"3D 변환 실패: {conv_err}")

            if stl_out.exists() and stl_out.stat().st_size > 0:
                stl_path = stl_out
            else:
                raise HTTPException(400, detail="STL 변환 결과 파일이 생성되지 않았습니다.")

        from core.stl_parser import STLParser
        parser = STLParser()
        result = parser.parse(stl_path)

        bbox = STLBBox(**result["bbox"]) if result["bbox"] else None
        return STLViewerResponse(
            vertices=result["vertices"],
            normals=result["normals"],
            triangle_count=result["triangle_count"],
            vertex_count=result["vertex_count"],
            bbox=bbox,
            format=result["format"],
            file_size_bytes=result["file_size_bytes"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise safe_error(e, "3D 파일 파싱")
    finally:
        tmp.unlink(missing_ok=True)
