"""
DXF → SVG 변환 + 레이어/엔티티 메타데이터 추출.

ezdxf의 좌표를 직접 SVG path로 변환하여
브라우저에서 pan/zoom/레이어 토글이 가능한 인터랙티브 뷰어를 지원한다.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

import ezdxf
from ezdxf.math import Vec3
from loguru import logger


# ── 기본 DXF 색상 (ACI → hex) ── 최소 16색
_ACI_COLORS = {
    0: "#000000",
    1: "#FF0000",
    2: "#FFFF00",
    3: "#00FF00",
    4: "#00FFFF",
    5: "#0000FF",
    6: "#FF00FF",
    7: "#000000",
    8: "#808080",
    9: "#C0C0C0",
    10: "#FF0000",
    11: "#FFAAAA",
    12: "#BD0000",
    13: "#BD7E7E",
    14: "#810000",
    15: "#815656",
}


def _aci_to_hex(aci: int) -> str:
    """AutoCAD Color Index → hex."""
    return _ACI_COLORS.get(aci, "#000000")


def _entity_color(entity) -> str:
    """엔티티의 실제 표시 색상을 결정한다."""
    try:
        color = entity.dxf.color
        if color == 256:  # BYLAYER
            layer = entity.doc.layers.get(entity.dxf.layer) if entity.doc else None
            if layer:
                color = layer.color
        if color == 0:  # BYBLOCK
            color = 7
        return _aci_to_hex(color)
    except Exception:
        return "#000000"


class DXFToSVG:
    """DXF → SVG 변환기. 레이어별 그룹핑 + 엔티티 메타데이터."""

    def __init__(self, precision: int = 2):
        self.precision = precision

    def convert(self, dxf_path: str | Path) -> dict:
        """DXF를 SVG 문자열 + 메타데이터로 변환.

        Returns:
            {
                "svg": str,               # 완전한 SVG XML 문자열
                "layers": [               # 레이어 목록
                    {"name": str, "color": str, "entity_count": int, "visible": bool}
                ],
                "entities": {             # 엔티티 타입별 개수
                    "LINE": n, "CIRCLE": n, ...
                },
                "total_entities": int,
                "bbox": {"min_x": f, "min_y": f, "max_x": f, "max_y": f} | None,
            }
        """
        doc = ezdxf.readfile(str(dxf_path))
        msp = doc.modelspace()
        all_entities = list(msp)

        if not all_entities:
            return {
                "svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"/>',
                "layers": [],
                "entities": {},
                "total_entities": 0,
                "bbox": None,
            }

        # ── BBox 계산 ──
        bbox = self._compute_bbox(msp)

        # ── 여백 및 뷰박스 ──
        if bbox:
            margin = max(bbox["max_x"] - bbox["min_x"], bbox["max_y"] - bbox["min_y"]) * 0.05
            vb_x = bbox["min_x"] - margin
            vb_y = bbox["min_y"] - margin
            vb_w = (bbox["max_x"] - bbox["min_x"]) + 2 * margin
            vb_h = (bbox["max_y"] - bbox["min_y"]) + 2 * margin
        else:
            vb_x, vb_y, vb_w, vb_h = 0, 0, 1000, 1000

        # ── 레이어별 엔티티 수집 ──
        layer_entities: dict[str, list] = defaultdict(list)
        entity_counts: Counter = Counter()
        layer_info: dict[str, dict] = {}

        for e in all_entities:
            layer_name = e.dxf.layer if hasattr(e.dxf, "layer") else "0"
            layer_entities[layer_name].append(e)
            entity_counts[e.dxftype()] += 1

        # 레이어 색상 (doc.layers 기준)
        for layer_name in layer_entities:
            try:
                layer_obj = doc.layers.get(layer_name)
                color = _aci_to_hex(layer_obj.color) if layer_obj else "#000000"
            except Exception:
                color = "#000000"
            layer_info[layer_name] = {
                "name": layer_name,
                "color": color,
                "entity_count": len(layer_entities[layer_name]),
                "visible": True,
            }

        # ── SVG 조립 ──
        svg_parts: list[str] = []
        svg_parts.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="{self._f(vb_x)} {self._f(-vb_y - vb_h)} {self._f(vb_w)} {self._f(vb_h)}" '
            f'width="100%" height="100%" '
            f'style="background:#FFFFFF">'
        )
        # Y축 반전 (DXF: Y up → SVG: Y down)
        svg_parts.append('<g transform="scale(1,-1)">')

        for layer_name, entities in sorted(layer_entities.items()):
            escaped_name = escape(layer_name)
            svg_parts.append(f'<g id="layer-{escaped_name}" class="dxf-layer" data-layer="{escaped_name}">')
            for e in entities:
                svg_el = self._entity_to_svg(e)
                if svg_el:
                    svg_parts.append(svg_el)
            svg_parts.append("</g>")

        svg_parts.append("</g>")
        svg_parts.append("</svg>")

        return {
            "svg": "\n".join(svg_parts),
            "layers": list(layer_info.values()),
            "entities": dict(entity_counts),
            "total_entities": len(all_entities),
            "bbox": bbox,
        }

    # ────────────────────────────────────────
    # 엔티티 → SVG 변환
    # ────────────────────────────────────────

    def _entity_to_svg(self, entity) -> str | None:
        """단일 엔티티 → SVG element 문자열."""
        t = entity.dxftype()
        color = _entity_color(entity)
        try:
            if t == "LINE":
                return self._line(entity, color)
            elif t == "CIRCLE":
                return self._circle(entity, color)
            elif t == "ARC":
                return self._arc(entity, color)
            elif t == "LWPOLYLINE":
                return self._lwpolyline(entity, color)
            elif t == "POLYLINE":
                return self._polyline(entity, color)
            elif t == "ELLIPSE":
                return self._ellipse(entity, color)
            elif t == "SPLINE":
                return self._spline(entity, color)
            elif t == "POINT":
                return self._point(entity, color)
            elif t == "TEXT":
                return self._text(entity, color)
            elif t == "MTEXT":
                return self._mtext(entity, color)
            elif t == "INSERT":
                return None  # 블록 참조는 복잡 — 스킵
            else:
                return None
        except Exception:
            return None

    def _line(self, e, color: str) -> str:
        s, end = e.dxf.start, e.dxf.end
        return (
            f'<line x1="{self._f(s.x)}" y1="{self._f(s.y)}" '
            f'x2="{self._f(end.x)}" y2="{self._f(end.y)}" '
            f'stroke="{color}" stroke-width="0.5" fill="none" '
            f'data-type="LINE"/>'
        )

    def _circle(self, e, color: str) -> str:
        c = e.dxf.center
        r = e.dxf.radius
        return (
            f'<circle cx="{self._f(c.x)}" cy="{self._f(c.y)}" r="{self._f(r)}" '
            f'stroke="{color}" stroke-width="0.5" fill="none" '
            f'data-type="CIRCLE" data-radius="{self._f(r)}"/>'
        )

    def _arc(self, e, color: str) -> str:
        c = e.dxf.center
        r = e.dxf.radius
        sa = math.radians(e.dxf.start_angle)
        ea = math.radians(e.dxf.end_angle)
        sx = c.x + r * math.cos(sa)
        sy = c.y + r * math.sin(sa)
        ex = c.x + r * math.cos(ea)
        ey = c.y + r * math.sin(ea)
        diff = (e.dxf.end_angle - e.dxf.start_angle) % 360
        large = 1 if diff > 180 else 0
        return (
            f'<path d="M{self._f(sx)},{self._f(sy)} '
            f'A{self._f(r)},{self._f(r)} 0 {large},1 {self._f(ex)},{self._f(ey)}" '
            f'stroke="{color}" stroke-width="0.5" fill="none" '
            f'data-type="ARC"/>'
        )

    def _lwpolyline(self, e, color: str) -> str:
        points = list(e.get_points(format="xy"))
        if len(points) < 2:
            return ""
        d = f"M{self._f(points[0][0])},{self._f(points[0][1])}"
        for x, y in points[1:]:
            d += f" L{self._f(x)},{self._f(y)}"
        if e.closed:
            d += " Z"
        return (
            f'<path d="{d}" stroke="{color}" stroke-width="0.5" fill="none" '
            f'data-type="LWPOLYLINE"/>'
        )

    def _polyline(self, e, color: str) -> str:
        points = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
        if len(points) < 2:
            return ""
        d = f"M{self._f(points[0][0])},{self._f(points[0][1])}"
        for x, y in points[1:]:
            d += f" L{self._f(x)},{self._f(y)}"
        if e.is_closed:
            d += " Z"
        return (
            f'<path d="{d}" stroke="{color}" stroke-width="0.5" fill="none" '
            f'data-type="POLYLINE"/>'
        )

    def _ellipse(self, e, color: str) -> str:
        c = e.dxf.center
        major = e.dxf.major_axis
        rx = math.sqrt(major.x ** 2 + major.y ** 2)
        ry = rx * e.dxf.ratio
        angle = math.degrees(math.atan2(major.y, major.x))
        return (
            f'<ellipse cx="{self._f(c.x)}" cy="{self._f(c.y)}" '
            f'rx="{self._f(rx)}" ry="{self._f(ry)}" '
            f'transform="rotate({self._f(angle)} {self._f(c.x)} {self._f(c.y)})" '
            f'stroke="{color}" stroke-width="0.5" fill="none" '
            f'data-type="ELLIPSE"/>'
        )

    def _spline(self, e, color: str) -> str:
        """스플라인 → 제어점 기반 polyline 근사."""
        try:
            pts = list(e.flattening(0.5))
        except Exception:
            pts = list(e.control_points)
        if len(pts) < 2:
            return ""
        d = f"M{self._f(pts[0].x)},{self._f(pts[0].y)}"
        for p in pts[1:]:
            d += f" L{self._f(p.x)},{self._f(p.y)}"
        return (
            f'<path d="{d}" stroke="{color}" stroke-width="0.5" fill="none" '
            f'data-type="SPLINE"/>'
        )

    def _point(self, e, color: str) -> str:
        p = e.dxf.location
        return (
            f'<circle cx="{self._f(p.x)}" cy="{self._f(p.y)}" r="0.5" '
            f'fill="{color}" data-type="POINT"/>'
        )

    def _text(self, e, color: str) -> str:
        ip = e.dxf.insert
        h = getattr(e.dxf, "height", 2.5) or 2.5
        txt = escape(e.dxf.text or "")
        # SVG Y 반전이므로 텍스트도 반전 보정
        return (
            f'<text x="{self._f(ip.x)}" y="{self._f(ip.y)}" '
            f'font-size="{self._f(h)}" fill="{color}" '
            f'transform="scale(1,-1) translate(0,{self._f(-2*ip.y)})" '
            f'data-type="TEXT">{txt}</text>'
        )

    def _mtext(self, e, color: str) -> str:
        ip = e.dxf.insert
        h = getattr(e.dxf, "char_height", 2.5) or 2.5
        txt = escape(e.text or "")
        return (
            f'<text x="{self._f(ip.x)}" y="{self._f(ip.y)}" '
            f'font-size="{self._f(h)}" fill="{color}" '
            f'transform="scale(1,-1) translate(0,{self._f(-2*ip.y)})" '
            f'data-type="MTEXT">{txt}</text>'
        )

    # ── 유틸리티 ──

    def _f(self, v: float) -> str:
        return f"{v:.{self.precision}f}"

    def _compute_bbox(self, msp) -> dict | None:
        try:
            from ezdxf import bbox as ezdxf_bbox
            cache = ezdxf_bbox.Cache()
            result = ezdxf_bbox.extents(msp, cache=cache)
            if result.has_data:
                return {
                    "min_x": round(result.extmin.x, self.precision),
                    "min_y": round(result.extmin.y, self.precision),
                    "max_x": round(result.extmax.x, self.precision),
                    "max_y": round(result.extmax.y, self.precision),
                }
        except Exception:
            pass
        return None
