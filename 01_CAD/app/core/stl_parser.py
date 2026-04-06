"""
STL 파서 + Three.js용 JSON 메시 변환.

Binary/ASCII STL을 파싱하여 vertices + normals + 메타데이터를 추출한다.
추가 의존성 없이 struct + numpy만 사용.
"""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np
from loguru import logger


class STLParser:
    """STL → 메시 데이터 + 메타데이터 추출."""

    def parse(self, stl_path: str | Path) -> dict:
        """STL 파일을 파싱하여 Three.js 호환 데이터를 반환.

        Returns:
            {
                "vertices": list[float],       # [x,y,z, x,y,z, ...] flat array
                "normals": list[float],         # [nx,ny,nz, ...] per-vertex normal
                "triangle_count": int,
                "vertex_count": int,
                "bbox": {
                    "min": [x, y, z],
                    "max": [x, y, z],
                    "center": [x, y, z],
                    "size": [w, h, d],
                },
                "format": "binary" | "ascii",
                "file_size_bytes": int,
            }
        """
        path = Path(stl_path)
        raw = path.read_bytes()
        file_size = len(raw)

        if self._is_binary(raw):
            triangles, fmt = self._parse_binary(raw), "binary"
        else:
            triangles, fmt = self._parse_ascii(raw.decode("utf-8", errors="replace")), "ascii"

        if not triangles:
            return {
                "vertices": [],
                "normals": [],
                "triangle_count": 0,
                "vertex_count": 0,
                "bbox": None,
                "format": fmt,
                "file_size_bytes": file_size,
            }

        # triangles: list of (normal, v1, v2, v3)  각각 (x,y,z) tuple
        vertices: list[float] = []
        normals: list[float] = []

        for normal, v1, v2, v3 in triangles:
            for v in (v1, v2, v3):
                vertices.extend(v)
                normals.extend(normal)

        verts_np = np.array(vertices, dtype=np.float32).reshape(-1, 3)
        bbox_min = verts_np.min(axis=0).tolist()
        bbox_max = verts_np.max(axis=0).tolist()
        bbox_center = ((verts_np.min(axis=0) + verts_np.max(axis=0)) / 2).tolist()
        bbox_size = (verts_np.max(axis=0) - verts_np.min(axis=0)).tolist()

        logger.info(
            f"STL 파싱 완료: {path.name}, {len(triangles)} triangles, "
            f"format={fmt}, size={file_size:,} bytes"
        )

        return {
            "vertices": [round(float(v), 4) for v in vertices],
            "normals": [round(float(n), 4) for n in normals],
            "triangle_count": len(triangles),
            "vertex_count": len(triangles) * 3,
            "bbox": {
                "min": [round(v, 4) for v in bbox_min],
                "max": [round(v, 4) for v in bbox_max],
                "center": [round(v, 4) for v in bbox_center],
                "size": [round(v, 4) for v in bbox_size],
            },
            "format": fmt,
            "file_size_bytes": file_size,
        }

    # ── 바이너리 STL ──

    @staticmethod
    def _is_binary(raw: bytes) -> bool:
        """바이너리 STL 여부 판별.
        바이너리 STL: 80-byte header + 4-byte triangle count + 50*n bytes.
        """
        if len(raw) < 84:
            return False
        # ASCII STL은 "solid"로 시작
        header = raw[:80]
        if header.lstrip().lower().startswith(b"solid"):
            # 하지만 binary STL도 "solid"로 시작할 수 있음 — 크기로 검증
            num_triangles = struct.unpack_from("<I", raw, 80)[0]
            expected_size = 84 + num_triangles * 50
            if expected_size == len(raw):
                return True
            # ASCII일 가능성
            return False
        return True

    @staticmethod
    def _parse_binary(raw: bytes) -> list[tuple]:
        """바이너리 STL → triangles 리스트."""
        num_triangles = struct.unpack_from("<I", raw, 80)[0]
        triangles = []
        offset = 84

        for _ in range(num_triangles):
            if offset + 50 > len(raw):
                break
            data = struct.unpack_from("<12fH", raw, offset)
            normal = (data[0], data[1], data[2])
            v1 = (data[3], data[4], data[5])
            v2 = (data[6], data[7], data[8])
            v3 = (data[9], data[10], data[11])
            triangles.append((normal, v1, v2, v3))
            offset += 50

        return triangles

    @staticmethod
    def _parse_ascii(text: str) -> list[tuple]:
        """ASCII STL → triangles 리스트."""
        import re
        triangles = []
        # facet normal nx ny nz
        facet_pattern = re.compile(
            r"facet\s+normal\s+([-+eE.\d]+)\s+([-+eE.\d]+)\s+([-+eE.\d]+)",
            re.IGNORECASE,
        )
        vertex_pattern = re.compile(
            r"vertex\s+([-+eE.\d]+)\s+([-+eE.\d]+)\s+([-+eE.\d]+)",
            re.IGNORECASE,
        )

        current_normal = (0.0, 0.0, 0.0)
        current_verts: list[tuple] = []

        for line in text.splitlines():
            line = line.strip()
            m = facet_pattern.match(line)
            if m:
                current_normal = (float(m.group(1)), float(m.group(2)), float(m.group(3)))
                current_verts = []
                continue

            m = vertex_pattern.match(line)
            if m:
                current_verts.append((float(m.group(1)), float(m.group(2)), float(m.group(3))))
                if len(current_verts) == 3:
                    triangles.append((current_normal, current_verts[0], current_verts[1], current_verts[2]))
                continue

        return triangles
