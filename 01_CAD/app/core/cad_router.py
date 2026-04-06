"""Universal CAD Format Router — 모든 파일 형식의 단일 진입점.

사용법:
    from core.cad_router import ensure_processable
    result = ensure_processable("/path/to/drawing.dxf")
    if result.status == "ready" or result.status == "converted":
        # result.png_path 사용
    elif result.status == "unsupported":
        # result.guidance 표시

새 형식 추가:
    register_handler([".xxx"], _handle_xxx)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from loguru import logger

from core.models import ProcessableResult


# ---------------------------------------------------------------------------
# Handler Registry (Strategy Pattern)
# ---------------------------------------------------------------------------

_HANDLERS: dict[str, Callable[[str, str], ProcessableResult]] = {}


def register_handler(extensions: list[str], handler_fn: Callable):
    """핸들러 등록 — 새 형식 추가 시 이 함수만 호출."""
    for ext in extensions:
        _HANDLERS[ext.lower()] = handler_fn


def supported_extensions() -> list[str]:
    """지원하는 모든 확장자 목록."""
    image_exts = [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]
    return sorted(image_exts + list(_HANDLERS.keys()))


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def ensure_processable(
    file_path: str | Path,
    output_dir: str | Path = "/tmp/cad_converted",
) -> ProcessableResult:
    """모든 CAD 파일을 파이프라인이 처리할 수 있는 형태로 변환.

    Args:
        file_path: 원본 파일 경로
        output_dir: 변환 결과 저장 디렉토리

    Returns:
        ProcessableResult (status: "ready" | "converted" | "unsupported")
    """
    file_path = Path(file_path)
    output_dir = Path(output_dir)

    if not file_path.exists():
        return ProcessableResult(
            status="unsupported",
            source_format="",
            guidance=f"파일이 존재하지 않습니다: {file_path}",
        )

    ext = file_path.suffix.lower()

    # 이미지는 직접 사용
    if ext in {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}:
        return ProcessableResult(
            status="ready",
            png_path=str(file_path),
            source_format=ext.lstrip("."),
        )

    # 등록된 핸들러로 라우팅
    handler = _HANDLERS.get(ext)
    if handler:
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            result = handler(str(file_path), str(output_dir))
            logger.info(
                f"CAD Router: {file_path.name} ({ext}) → {result.status}"
            )
            return result
        except Exception as e:
            logger.error(f"CAD Router 변환 실패: {file_path.name} — {e}")
            return ProcessableResult(
                status="unsupported",
                source_format=ext.lstrip("."),
                guidance=f"'{ext}' 파일 변환 중 오류 발생: {e}",
            )

    # 미지원 형식
    supported = ", ".join(supported_extensions())
    return ProcessableResult(
        status="unsupported",
        source_format=ext.lstrip("."),
        guidance=_get_guidance(ext, supported),
    )


# ---------------------------------------------------------------------------
# Guidance Messages for Unsupported Formats
# ---------------------------------------------------------------------------

_PROPRIETARY_GUIDANCE = {
    ".catpart": "CATIA 파일은 STEP(.stp)으로 내보내기 후 업로드해주세요. "
                "CATIA > File > Save As > STEP AP214",
    ".catproduct": "CATIA 어셈블리는 STEP(.stp)으로 내보내기 후 업로드해주세요.",
    ".prt": "NX/Creo 파일은 STEP(.stp)으로 내보내기 후 업로드해주세요. "
            "File > Export > STEP",
    ".sldprt": "SolidWorks 파일은 STEP(.stp)으로 내보내기 후 업로드해주세요. "
               "File > Save As > STEP",
    ".sldasm": "SolidWorks 어셈블리는 STEP(.stp)으로 내보내기 후 업로드해주세요.",
    ".x_t": "Parasolid 파일은 STEP(.stp)으로 변환 후 업로드해주세요.",
    ".x_b": "Parasolid 바이너리는 STEP(.stp)으로 변환 후 업로드해주세요.",
    ".3dm": "Rhino 파일은 STEP(.stp) 또는 IGES(.igs)로 내보내기 후 업로드해주세요.",
    ".ipt": "Inventor 파일은 STEP(.stp)으로 내보내기 후 업로드해주세요.",
    ".iam": "Inventor 어셈블리는 STEP(.stp)으로 내보내기 후 업로드해주세요.",
}


def _get_guidance(ext: str, supported: str) -> str:
    """확장자별 안내 메시지 생성."""
    if ext in _PROPRIETARY_GUIDANCE:
        return _PROPRIETARY_GUIDANCE[ext]
    return f"'{ext}' 형식은 지원하지 않습니다. 지원 형식: {supported}"


# ---------------------------------------------------------------------------
# Handler Implementations
# ---------------------------------------------------------------------------

def _handle_dxf(file_path: str, output_dir: str) -> ProcessableResult:
    """DXF → PNG (ezdxf + matplotlib)."""
    from core.dxf_renderer import DXFRenderer

    renderer = DXFRenderer()
    src = Path(file_path)
    out_png = Path(output_dir) / f"{src.stem}.png"

    png_path = renderer.render_to_png(src, out_png)
    metadata = renderer.extract_metadata(src)

    return ProcessableResult(
        status="converted",
        png_path=str(png_path),
        dxf_path=file_path,
        source_format="dxf",
        metadata=metadata,
    )


def _handle_dwg(file_path: str, output_dir: str) -> ProcessableResult:
    """DWG → ODA Converter → DXF → DXF 핸들러."""
    try:
        import ezdxf.addons.odafc as odafc
    except ImportError:
        return ProcessableResult(
            status="unsupported",
            source_format="dwg",
            guidance="DWG 변환에 필요한 ODA File Converter가 설치되지 않았습니다. "
                     "https://www.opendesign.com/guestfiles/oda_file_converter 에서 "
                     "다운로드 후 설치해주세요.",
        )

    src = Path(file_path)
    dxf_out = Path(output_dir) / f"{src.stem}.dxf"

    try:
        odafc.convert(str(src), str(dxf_out))
    except Exception as e:
        return ProcessableResult(
            status="unsupported",
            source_format="dwg",
            guidance=f"DWG → DXF 변환 실패: {e}. "
                     "ODA File Converter 설치를 확인해주세요.",
        )

    if not dxf_out.exists():
        return ProcessableResult(
            status="unsupported",
            source_format="dwg",
            guidance="DWG → DXF 변환 결과 파일이 생성되지 않았습니다.",
        )

    # DXF 핸들러로 위임
    result = _handle_dxf(str(dxf_out), output_dir)
    result.source_format = "dwg"
    return result


def _handle_step(file_path: str, output_dir: str) -> ProcessableResult:
    """STEP → CadQuery → STL → matplotlib → PNG."""
    try:
        import cadquery as cq
    except ImportError:
        return ProcessableResult(
            status="unsupported",
            source_format="step",
            guidance="STEP 파일 처리에 필요한 CadQuery가 설치되지 않았습니다. "
                     "pip install cadquery 로 설치해주세요.",
        )

    src = Path(file_path)
    out_png = Path(output_dir) / f"{src.stem}.png"

    try:
        shape = cq.importers.importStep(str(src))
        bb = shape.val().BoundingBox()
        metadata = {
            "bounding_box": {
                "x_len": round(bb.xlen, 3),
                "y_len": round(bb.ylen, 3),
                "z_len": round(bb.zlen, 3),
            },
            "format": "step",
        }

        # CadQuery → STL → matplotlib 3D 렌더링
        stl_tmp = Path(output_dir) / f"{src.stem}_tmp.stl"
        cq.exporters.export(shape, str(stl_tmp), exportType="STL")

        if stl_tmp.exists():
            _render_stl_to_png(stl_tmp, out_png)
            stl_tmp.unlink(missing_ok=True)
        else:
            raise RuntimeError("STL 변환 실패")

        return ProcessableResult(
            status="converted",
            png_path=str(out_png),
            source_format="step",
            metadata=metadata,
        )
    except Exception as e:
        return ProcessableResult(
            status="unsupported",
            source_format="step",
            guidance=f"STEP 파일 처리 중 오류: {e}",
        )


def _handle_iges(file_path: str, output_dir: str) -> ProcessableResult:
    """IGES → OCP/CadQuery → STL → matplotlib → PNG."""
    # OCP 직접 또는 CadQuery 경유 시도
    try:
        from OCP.IGESControl import IGESControl_Reader
        from OCP.IFSelect import IFSelect_RetDone
        from OCP.StlAPI import StlAPI_Writer
    except ImportError:
        return ProcessableResult(
            status="unsupported",
            source_format="iges",
            guidance="IGES 파일 처리에 필요한 OCP(OpenCascade Python)가 "
                     "설치되지 않았습니다. "
                     "pip install cadquery (OCP 포함) 로 설치해주세요.",
        )

    src = Path(file_path)
    out_png = Path(output_dir) / f"{src.stem}.png"
    stl_tmp = Path(output_dir) / f"{src.stem}_tmp.stl"

    try:
        reader = IGESControl_Reader()
        status = reader.ReadFile(str(src))
        if status != IFSelect_RetDone:
            return ProcessableResult(
                status="unsupported",
                source_format="iges",
                guidance=f"IGES 파일 읽기 실패: {src.name}",
            )

        reader.TransferRoots()
        shape = reader.OneShape()

        # OCP Shape → STL → matplotlib
        writer = StlAPI_Writer()
        writer.Write(shape, str(stl_tmp))

        if stl_tmp.exists():
            _render_stl_to_png(stl_tmp, out_png)
            stl_tmp.unlink(missing_ok=True)
        else:
            raise RuntimeError("STL 변환 실패")

        return ProcessableResult(
            status="converted",
            png_path=str(out_png),
            source_format="iges",
            metadata={"format": "iges"},
        )
    except Exception as e:
        return ProcessableResult(
            status="unsupported",
            source_format="iges",
            guidance=f"IGES 파일 처리 중 오류: {e}",
        )


def _handle_stl(file_path: str, output_dir: str) -> ProcessableResult:
    """STL → numpy-stl + matplotlib → PNG."""
    try:
        from stl import mesh as stl_mesh
    except ImportError:
        return ProcessableResult(
            status="unsupported",
            source_format="stl",
            guidance="STL 파일 처리에 필요한 numpy-stl이 설치되지 않았습니다. "
                     "pip install numpy-stl 로 설치해주세요.",
        )

    src = Path(file_path)
    out_png = Path(output_dir) / f"{src.stem}.png"

    try:
        stl_data = stl_mesh.Mesh.from_file(str(src))

        # 공통 헬퍼로 렌더링
        _render_stl_to_png(src, out_png)

        # 메타데이터 추출
        metadata = {
            "triangle_count": len(stl_data.vectors),
            "bounding_box": {
                "min": stl_data.min_.tolist(),
                "max": stl_data.max_.tolist(),
            },
            "format": "stl",
        }
        try:
            metadata["volume"] = float(stl_data.get_mass_properties()[0])
        except Exception:
            metadata["volume"] = 0

        return ProcessableResult(
            status="converted",
            png_path=str(out_png),
            source_format="stl",
            metadata=metadata,
        )
    except Exception as e:
        return ProcessableResult(
            status="unsupported",
            source_format="stl",
            guidance=f"STL 파일 처리 중 오류: {e}",
        )


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _render_stl_to_png(stl_path: Path, png_path: Path) -> None:
    """STL 파일 → matplotlib 3D → PNG 렌더링 (STEP/IGES/STL 공통 헬퍼)."""
    from stl import mesh as stl_mesh
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import art3d

    stl_data = stl_mesh.Mesh.from_file(str(stl_path))

    fig = plt.figure(figsize=(8, 8), dpi=150)
    ax = fig.add_subplot(111, projection="3d")

    poly = art3d.Poly3DCollection(stl_data.vectors, alpha=0.7)
    poly.set_facecolor("steelblue")
    poly.set_edgecolor("gray")
    ax.add_collection3d(poly)

    scale = stl_data.points.flatten()
    ax.auto_scale_xyz(
        [scale.min(), scale.max()],
        [scale.min(), scale.max()],
        [scale.min(), scale.max()],
    )
    ax.set_axis_off()

    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        str(png_path), dpi=150, bbox_inches="tight",
        pad_inches=0, facecolor="white",
    )
    plt.close(fig)


# ---------------------------------------------------------------------------
# Register All Handlers
# ---------------------------------------------------------------------------

register_handler([".dxf"], _handle_dxf)
register_handler([".dwg"], _handle_dwg)
register_handler([".stp", ".step"], _handle_step)
register_handler([".igs", ".iges"], _handle_iges)
register_handler([".stl"], _handle_stl)
