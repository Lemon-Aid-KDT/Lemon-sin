"""Universal Renderer — 포맷에 무관한 단일 렌더링 인터페이스.

사용법:
    from core.renderer import UniversalRenderer
    renderer = UniversalRenderer()

    # 썸네일 (256x256)
    result = renderer.render("/path/to/drawing.dxf", RenderMode.THUMBNAIL)

    # 풀사이즈 (1024x1024)
    result = renderer.render("/path/to/model.stl", RenderMode.FULL)

    # 인터랙티브 HTML (3D/2D viewer)
    result = renderer.render("/path/to/model.stl", RenderMode.INTERACTIVE)

기존 코드 래핑:
    - DXF: core/dxf_renderer.DXFRenderer.render_to_png()
    - STL: core/stl_parser.STLParser.parse() + matplotlib
    - PNG/JPG: 직접 복사 또는 리사이즈
    - STEP/IGES: CAD Router의 변환 결과 재사용
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from loguru import logger

from core.models import RenderMode, RenderResult


class UniversalRenderer:
    """포맷에 무관한 단일 렌더링 인터페이스."""

    _RENDER_CONFIGS = {
        RenderMode.THUMBNAIL: {"dpi": 72, "figsize": (4, 4), "max_px": 256},
        RenderMode.FULL: {"dpi": 150, "figsize": (8, 8), "max_px": 1024},
        RenderMode.INTERACTIVE: {"dpi": 150, "figsize": (8, 8), "max_px": 1024},
    }

    def __init__(self, cache_dir: str | Path = "/tmp/render_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def render(
        self,
        file_path: str | Path,
        mode: RenderMode = RenderMode.THUMBNAIL,
        force: bool = False,
    ) -> RenderResult:
        """파일을 렌더링한다.

        Args:
            file_path: 원본 파일 경로
            mode: 렌더링 모드 (THUMBNAIL, FULL, INTERACTIVE)
            force: True이면 캐시 무시하고 재렌더링

        Returns:
            RenderResult
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return RenderResult(
                mode=mode,
                metadata={"error": f"파일이 존재하지 않습니다: {file_path}"},
            )

        ext = file_path.suffix.lower()

        # 캐시 키 생성
        cache_key = self._cache_key(file_path, mode)
        cached_png = self.cache_dir / f"{cache_key}.png"

        if not force and cached_png.exists():
            return RenderResult(
                mode=mode,
                png_path=str(cached_png),
                metadata={"cached": True, "source_format": ext.lstrip(".")},
            )

        # 포맷별 렌더링 위임
        if ext in {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}:
            return self._render_image(file_path, cached_png, mode)
        elif ext == ".dxf":
            return self._render_dxf(file_path, cached_png, mode)
        elif ext == ".stl":
            return self._render_stl(file_path, cached_png, mode)
        elif ext in {".stp", ".step", ".igs", ".iges", ".dwg"}:
            return self._render_via_cad_router(file_path, cached_png, mode)
        else:
            return RenderResult(
                mode=mode,
                metadata={"error": f"렌더링 미지원 형식: {ext}"},
            )

    def render_thumbnail(self, file_path: str | Path) -> str | None:
        """편의 메서드: 썸네일 PNG 경로 반환 (없으면 None)."""
        result = self.render(file_path, RenderMode.THUMBNAIL)
        return result.png_path

    # ------------------------------------------------------------------
    # Format-specific renderers
    # ------------------------------------------------------------------

    def _render_image(
        self, src: Path, dst: Path, mode: RenderMode
    ) -> RenderResult:
        """이미지 파일 → 리사이즈 또는 복사."""
        config = self._RENDER_CONFIGS[mode]

        try:
            from PIL import Image

            img = Image.open(src)
            max_px = config["max_px"]

            if max(img.size) > max_px:
                img.thumbnail((max_px, max_px), Image.LANCZOS)

            dst.parent.mkdir(parents=True, exist_ok=True)
            img.save(str(dst), "PNG")
        except ImportError:
            # PIL 없으면 원본 복사
            shutil.copy2(src, dst)
        except Exception:
            # 손상된 이미지 등 — 원본 복사 폴백
            shutil.copy2(src, dst)

        return RenderResult(
            mode=mode,
            png_path=str(dst),
            metadata={"source_format": src.suffix.lstrip(".")},
        )

    def _render_dxf(
        self, src: Path, dst: Path, mode: RenderMode
    ) -> RenderResult:
        """DXF → PNG (기존 DXFRenderer 래핑)."""
        from core.dxf_renderer import DXFRenderer

        config = self._RENDER_CONFIGS[mode]
        renderer = DXFRenderer(
            dpi=config["dpi"],
            figsize=config["figsize"],
        )

        try:
            png_path = renderer.render_to_png(src, dst)
            metadata = renderer.extract_metadata(src)
            metadata["source_format"] = "dxf"

            if mode == RenderMode.INTERACTIVE:
                html = self._build_dxf_interactive_viewer(src, str(png_path))
                return RenderResult(
                    mode=mode,
                    png_path=str(png_path),
                    html_viewer=html,
                    metadata=metadata,
                )

            return RenderResult(
                mode=mode,
                png_path=str(png_path),
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"DXF 렌더링 실패: {src.name} — {e}")
            return RenderResult(
                mode=mode,
                metadata={"error": str(e), "source_format": "dxf"},
            )

    def _render_stl(
        self, src: Path, dst: Path, mode: RenderMode
    ) -> RenderResult:
        """STL → matplotlib 3D → PNG."""
        try:
            from stl import mesh as stl_mesh
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from mpl_toolkits.mplot3d import art3d

            config = self._RENDER_CONFIGS[mode]
            stl_data = stl_mesh.Mesh.from_file(str(src))

            fig = plt.figure(figsize=config["figsize"], dpi=config["dpi"])
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

            dst.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(
                str(dst), dpi=config["dpi"],
                bbox_inches="tight", pad_inches=0, facecolor="white",
            )
            plt.close(fig)

            metadata = {
                "triangle_count": len(stl_data.vectors),
                "source_format": "stl",
            }

            if mode == RenderMode.INTERACTIVE:
                html = self._build_stl_interactive_viewer(src)
                return RenderResult(
                    mode=mode, png_path=str(dst),
                    html_viewer=html, metadata=metadata,
                )

            return RenderResult(mode=mode, png_path=str(dst), metadata=metadata)

        except ImportError:
            return RenderResult(
                mode=mode,
                metadata={
                    "error": "numpy-stl이 설치되지 않았습니다",
                    "source_format": "stl",
                },
            )
        except Exception as e:
            logger.error(f"STL 렌더링 실패: {src.name} — {e}")
            return RenderResult(
                mode=mode,
                metadata={"error": str(e), "source_format": "stl"},
            )

    def _render_via_cad_router(
        self, src: Path, dst: Path, mode: RenderMode
    ) -> RenderResult:
        """STEP/IGES/DWG → CAD Router 변환 후 이미지 렌더링."""
        from core.cad_router import ensure_processable

        result = ensure_processable(str(src), str(dst.parent))
        if result.status in ("ready", "converted") and result.png_path:
            # CAD Router 결과를 캐시 경로로 복사
            if Path(result.png_path) != dst:
                shutil.copy2(result.png_path, dst)
            return RenderResult(
                mode=mode,
                png_path=str(dst),
                metadata={
                    "source_format": result.source_format,
                    **result.metadata,
                },
            )
        return RenderResult(
            mode=mode,
            metadata={
                "error": result.guidance or "변환 실패",
                "source_format": result.source_format,
            },
        )

    # ------------------------------------------------------------------
    # Interactive Viewers (HTML)
    # ------------------------------------------------------------------

    @staticmethod
    def _build_dxf_interactive_viewer(
        dxf_path: Path, png_path: str
    ) -> str:
        """DXF 인터랙티브 뷰어 HTML 생성 (줌/팬/회전)."""
        return f"""
        <div id="dxf-viewer" style="position:relative; width:100%; background:#1a1a1a;">
            <div style="padding:8px; display:flex; gap:8px;">
                <button onclick="zoomIn()">+ Zoom</button>
                <button onclick="zoomOut()">- Zoom</button>
                <button onclick="fitScreen()">Fit</button>
                <button onclick="rotate()">Rotate</button>
            </div>
            <img id="dxf-img" src="{png_path}" style="max-width:100%; transform-origin:center;"
                 alt="{dxf_path.name}" />
        </div>
        <script>
            let scale = 1, rot = 0;
            const img = document.getElementById('dxf-img');
            function zoomIn() {{ scale = Math.min(scale * 1.2, 5); update(); }}
            function zoomOut() {{ scale = Math.max(scale / 1.2, 0.2); update(); }}
            function fitScreen() {{ scale = 1; rot = 0; update(); }}
            function rotate() {{ rot = (rot + 90) % 360; update(); }}
            function update() {{ img.style.transform = `scale(${{scale}}) rotate(${{rot}}deg)`; }}
        </script>
        """

    @staticmethod
    def _build_stl_interactive_viewer(stl_path: Path) -> str:
        """STL Three.js 인터랙티브 뷰어 HTML (placeholder)."""
        return f"""
        <div style="padding:20px; background:#1a1a1a; color:#ccc; text-align:center;">
            <p>3D Viewer: {stl_path.name}</p>
            <p style="font-size:12px; color:#888;">
                인터랙티브 3D 뷰어는 Three.js 통합 후 활성화됩니다.
            </p>
        </div>
        """

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------

    @staticmethod
    def _cache_key(file_path: Path, mode: RenderMode) -> str:
        """파일 경로 + 수정시간 + 모드 기반 캐시 키."""
        stat = file_path.stat()
        raw = f"{file_path}:{stat.st_mtime}:{stat.st_size}:{mode.value}"
        return hashlib.md5(raw.encode()).hexdigest()

    def clear_cache(self) -> int:
        """캐시 디렉토리 비우기. 삭제된 파일 수 반환."""
        count = 0
        for f in self.cache_dir.glob("*.png"):
            f.unlink()
            count += 1
        return count
