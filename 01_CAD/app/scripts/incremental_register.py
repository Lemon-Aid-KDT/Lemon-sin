#!/usr/bin/env python3
"""
증분 도면 등록 스크립트.

디렉토리를 스캔하여 미등록 파일만 자동 등록한다.
--watch 모드로 실시간 감시도 가능.

사용법:
    python scripts/incremental_register.py ./data/sample_drawings --scan-only
    python scripts/incremental_register.py ./data/sample_drawings --watch
    python scripts/incremental_register.py ./data/sample_drawings --category Shafts
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".pdf", ".dxf"}


def scan_and_register(
    directory: Path,
    category: str = "",
    use_llm: bool = False,
) -> int:
    """디렉토리 전수 스캔 → 미등록 파일만 등록.

    Returns:
        등록된 파일 수
    """
    from core.dependencies import get_pipeline

    pipeline = get_pipeline()
    existing_names = {r.file_name for r in pipeline.get_all_records()}

    all_files = [
        f for f in sorted(directory.iterdir())
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS
    ]
    new_files = [f for f in all_files if f.name not in existing_names]

    logger.info(
        f"스캔 완료: 전체 {len(all_files)}건, "
        f"기등록 {len(all_files) - len(new_files)}건, "
        f"신규 {len(new_files)}건"
    )

    if not new_files:
        logger.info("신규 파일 없음. 종료.")
        return 0

    registered = 0
    for i, fpath in enumerate(new_files):
        try:
            record = pipeline.register_drawing(
                fpath,
                category=category,
                use_llm=use_llm,
                copy_to_store=True,
            )
            registered += 1
            similar_count = len(record.similar_drawings)
            similar_msg = f" (유사도면 {similar_count}건)" if similar_count else ""
            logger.info(
                f"[{i + 1}/{len(new_files)}] 등록: {fpath.name} "
                f"→ {record.drawing_id}{similar_msg}"
            )
        except Exception as e:
            logger.error(f"[{i + 1}/{len(new_files)}] 실패: {fpath.name}: {e}")

    logger.info(f"증분 등록 완료: {registered}/{len(new_files)}건")
    return registered


def watch_directory(
    directory: Path,
    category: str = "",
    use_llm: bool = False,
):
    """디렉토리를 실시간 감시하며 신규 파일을 자동 등록한다.

    watchdog 라이브러리 필요: pip install watchdog
    """
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        logger.error(
            "watchdog 미설치. 설치: pip install watchdog\n"
            "--scan-only 모드는 watchdog 없이 사용 가능합니다."
        )
        sys.exit(1)

    from core.dependencies import get_pipeline

    class _Handler(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory:
                return
            fpath = Path(event.src_path)
            if fpath.suffix.lower() not in SUPPORTED_EXTS:
                return
            # 파일 쓰기 완료 대기
            time.sleep(2)
            pipeline = get_pipeline()
            existing_names = {r.file_name for r in pipeline.get_all_records()}
            if fpath.name in existing_names:
                logger.debug(f"이미 등록됨: {fpath.name}")
                return
            try:
                record = pipeline.register_drawing(
                    fpath, category=category, use_llm=use_llm, copy_to_store=True,
                )
                logger.info(f"자동 등록: {fpath.name} → {record.drawing_id}")
            except Exception as e:
                logger.error(f"자동 등록 실패: {fpath.name}: {e}")

    observer = Observer()
    observer.schedule(_Handler(), str(directory), recursive=False)
    observer.start()
    logger.info(f"디렉토리 감시 시작: {directory} (Ctrl+C로 종료)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("감시 종료")
        observer.stop()
    observer.join()


def main():
    parser = argparse.ArgumentParser(description="증분 도면 등록")
    parser.add_argument("directory", help="대상 디렉토리")
    parser.add_argument("--category", default="", help="카테고리 지정")
    parser.add_argument("--use-llm", action="store_true", help="LLM 설명 생성")
    parser.add_argument(
        "--watch", action="store_true",
        help="디렉토리 실시간 감시 모드 (watchdog 필요)",
    )
    parser.add_argument(
        "--scan-only", action="store_true",
        help="1회 스캔만 실행 (기본값)",
    )
    args = parser.parse_args()

    directory = Path(args.directory)
    if not directory.is_dir():
        logger.error(f"디렉토리 없음: {directory}")
        sys.exit(1)

    # 초기 스캔
    scan_and_register(directory, args.category, args.use_llm)

    # 감시 모드
    if args.watch:
        watch_directory(directory, args.category, args.use_llm)


if __name__ == "__main__":
    main()
