"""
DXF -> PNG 렌더링 및 메타데이터 추출

ezdxf.addons.drawing + matplotlib Agg 백엔드로 headless 렌더링한다.
archive/experiments/B1_MiSUMi_대량등록/convert_dxf_to_png.py 로직 재사용.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import ezdxf
from loguru import logger


class DXFRenderer:
    """DXF -> PNG 렌더링 및 메타데이터 추출"""

    def __init__(self, dpi: int = 150, figsize: tuple[int, int] = (8, 8)):
        self.dpi = dpi
        self.figsize = figsize

    # ─────────────────────────────────────────────
    # 렌더링
    # ─────────────────────────────────────────────

    def render_to_png(self, dxf_path: Path, output_path: Path) -> Path:
        """DXF를 PNG로 렌더링한다.

        Args:
            dxf_path: 원본 DXF 파일 경로
            output_path: 출력 PNG 파일 경로

        Returns:
            output_path

        Raises:
            ezdxf.DXFError: DXF 파일 파싱 실패
            RuntimeError: 렌더링 실패
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from ezdxf.addons.drawing import RenderContext, Frontend
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

        doc = ezdxf.readfile(str(dxf_path))
        msp = doc.modelspace()

        fig = plt.figure(figsize=self.figsize, dpi=self.dpi)
        ax = fig.add_axes([0, 0, 1, 1])
        ctx = RenderContext(doc)
        out = MatplotlibBackend(ax)
        Frontend(ctx, out).draw_layout(msp, finalize=True)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(
            str(output_path),
            dpi=self.dpi,
            bbox_inches="tight",
            pad_inches=0,
            facecolor="white",
        )
        plt.close(fig)

        logger.info(f"DXF 렌더링 완료: {dxf_path.name} -> {output_path.name}")
        return output_path

    # ─────────────────────────────────────────────
    # 메타데이터 추출
    # ─────────────────────────────────────────────

    def extract_metadata(self, dxf_path: Path) -> dict:
        """DXF 메타데이터 추출.

        Returns:
            {
                "layers": [...],
                "entity_count": int,
                "entity_types": {"LINE": n, "CIRCLE": n, ...},
                "bounding_box": (min_x, min_y, max_x, max_y) | None,
            }
        """
        doc = ezdxf.readfile(str(dxf_path))
        msp = doc.modelspace()

        layers = [layer.dxf.name for layer in doc.layers]

        entities = list(msp)
        entity_types = dict(Counter(e.dxftype() for e in entities))

        bbox = None
        try:
            from ezdxf import bbox as ezdxf_bbox
            cache = ezdxf_bbox.Cache()
            result = ezdxf_bbox.extents(msp, cache=cache)
            if result.has_data:
                bbox = (
                    result.extmin.x,
                    result.extmin.y,
                    result.extmax.x,
                    result.extmax.y,
                )
        except Exception:
            pass

        return {
            "layers": layers,
            "entity_count": len(entities),
            "entity_types": entity_types,
            "bounding_box": bbox,
        }

    # ─────────────────────────────────────────────
    # 유틸리티
    # ─────────────────────────────────────────────

    @staticmethod
    def is_dxf(file_path: Path | str) -> bool:
        """DXF 파일인지 확인 (확장자 기반)"""
        return Path(file_path).suffix.lower() == ".dxf"
