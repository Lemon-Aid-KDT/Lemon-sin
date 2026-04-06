"""records.json -> SQLite 마이그레이션 스크립트

기존 records.json 파일을 SQLite 데이터베이스(records.db)로 변환한다.

사용법:
    python scripts/migrate_to_sqlite.py
    python scripts/migrate_to_sqlite.py --json-path ./data/vector_store/records.json
    python scripts/migrate_to_sqlite.py --db-path ./data/vector_store/records.db
"""

import argparse
import json
import sys
import time
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (app/ 디렉토리)
_SCRIPT_DIR = Path(__file__).resolve().parent
_APP_DIR = _SCRIPT_DIR.parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from loguru import logger
from core.record_store import RecordStore


def migrate(
    json_path: str = "./data/vector_store/records.json",
    db_path: str = "./data/vector_store/records.db",
    batch_size: int = 1000,
) -> None:
    """records.json을 SQLite로 마이그레이션한다.

    Args:
        json_path: 원본 records.json 경로
        db_path: 대상 SQLite DB 경로
        batch_size: 배치 커밋 단위
    """
    json_file = Path(json_path)
    if not json_file.exists():
        logger.error(f"records.json 파일이 없습니다: {json_file}")
        sys.exit(1)

    # 1. records.json 로드
    logger.info(f"records.json 로드 중: {json_file} ({json_file.stat().st_size / 1024 / 1024:.1f} MB)")
    t0 = time.time()
    with open(json_file, "r", encoding="utf-8") as f:
        data: dict = json.load(f)
    load_time = time.time() - t0
    logger.info(f"JSON 로드 완료: {len(data)}건 ({load_time:.2f}s)")

    # 2. RecordStore 생성
    store = RecordStore(db_path=db_path)

    # 3. 배치 삽입
    logger.info(f"SQLite 삽입 시작 (batch_size={batch_size})")
    t1 = time.time()

    # 하위 호환: 옛날 필드가 없는 레코드에 기본값 설정
    for rid, rdata in data.items():
        rdata.setdefault("drawing_id", rid)
        rdata.setdefault("file_path", "")
        rdata.setdefault("file_name", "")
        rdata.setdefault("category", "")
        rdata.setdefault("ocr_text", "")
        rdata.setdefault("part_numbers", [])
        rdata.setdefault("dimensions", [])
        rdata.setdefault("materials", [])
        rdata.setdefault("description", "")
        rdata.setdefault("metadata", {})
        rdata.setdefault("yolo_confidence", 0.0)
        rdata.setdefault("yolo_needs_review", False)
        rdata.setdefault("yolo_top_k", [])
        rdata.setdefault("detected_regions", [])
        rdata.setdefault("title_block_data", {})
        rdata.setdefault("parts_table_data", {})
        rdata.setdefault("detection_enhanced", False)
        rdata.setdefault("dxf_path", "")
        rdata.setdefault("similar_drawings", [])
        rdata.setdefault("registered_at", "")
        rdata.setdefault("revision", 1)

    inserted = store.add_batch(data, batch_size=batch_size)
    insert_time = time.time() - t1
    logger.info(f"SQLite 삽입 완료: {inserted}건 ({insert_time:.2f}s)")

    # 4. 검증
    db_count = store.count()
    json_count = len(data)

    if db_count == json_count:
        logger.info(f"검증 성공: JSON({json_count}) == SQLite({db_count})")
    else:
        logger.warning(f"검증 불일치: JSON({json_count}) != SQLite({db_count})")

    # 5. 요약
    db_file = Path(db_path)
    db_size_mb = db_file.stat().st_size / 1024 / 1024 if db_file.exists() else 0
    json_size_mb = json_file.stat().st_size / 1024 / 1024

    logger.info("=" * 50)
    logger.info("마이그레이션 완료 요약")
    logger.info(f"  원본: {json_file} ({json_size_mb:.1f} MB, {json_count}건)")
    logger.info(f"  대상: {db_file} ({db_size_mb:.1f} MB, {db_count}건)")
    logger.info(f"  JSON 로드: {load_time:.2f}s")
    logger.info(f"  SQLite 삽입: {insert_time:.2f}s")
    logger.info(f"  총 소요: {time.time() - t0:.2f}s")
    logger.info("=" * 50)

    store.close()


def main():
    parser = argparse.ArgumentParser(
        description="records.json -> SQLite 마이그레이션"
    )
    parser.add_argument(
        "--json-path",
        default="./data/vector_store/records.json",
        help="원본 records.json 경로 (기본: ./data/vector_store/records.json)",
    )
    parser.add_argument(
        "--db-path",
        default="./data/vector_store/records.db",
        help="대상 SQLite DB 경로 (기본: ./data/vector_store/records.db)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="배치 커밋 단위 (기본: 1000)",
    )
    args = parser.parse_args()
    migrate(
        json_path=args.json_path,
        db_path=args.db_path,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
