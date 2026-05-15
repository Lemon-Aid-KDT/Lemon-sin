"""애플리케이션 로깅 설정."""

from __future__ import annotations

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """루트 로거를 설정한다.

    Args:
        level: 로그 레벨 문자열.
    """
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
