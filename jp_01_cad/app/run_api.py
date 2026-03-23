#!/usr/bin/env python3
"""
CAD Vision REST API 실행 진입점.

사용법:
    python run_api.py
    python run_api.py --port 8000 --host 0.0.0.0
"""

import argparse

import uvicorn

from config.settings import settings


def main():
    parser = argparse.ArgumentParser(description="CAD Vision REST API")
    parser.add_argument("--host", default=settings.api_host)
    parser.add_argument("--port", type=int, default=settings.api_port)
    parser.add_argument("--reload", action="store_true", help="개발 모드 (자동 리로드)")
    args = parser.parse_args()

    uvicorn.run(
        "app.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
