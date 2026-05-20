"""공통 pytest 픽스처.

알고리즘 구현이 추가되면 회사 가이드 예시 사용자 fixture를 이 파일에 추가한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
