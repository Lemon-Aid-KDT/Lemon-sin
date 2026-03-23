"""SQLite 기반 레코드 저장소

records.json을 대체하여 SQLite DB로 도면 레코드를 관리한다.
- 동시 접근 지원 (WAL mode)
- 인덱스 기반 빠른 조회 (drawing_id, category, file_name)
- 트랜잭션으로 데이터 무결성 보장
"""

import json
import sqlite3
from pathlib import Path

from loguru import logger


class RecordStore:
    """SQLite 기반 도면 레코드 저장소.

    WAL 모드로 API + Streamlit 동시 접근을 지원하며,
    개별 레코드 단위로 읽기/쓰기가 가능하다.
    """

    # DrawingRecord 필드 중 JSON으로 직렬화할 리스트/딕트 컬럼
    _JSON_COLUMNS = frozenset({
        "part_numbers", "dimensions", "materials", "metadata",
        "yolo_top_k", "detected_regions", "title_block_data",
        "parts_table_data", "similar_drawings",
    })

    def __init__(self, db_path: str = "data/vector_store/records.db"):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(self._db_path),
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        self._init_db()
        logger.info(f"RecordStore 초기화: {self._db_path}")

    # ------------------------------------------------------------------
    # 스키마 초기화
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """테이블 및 인덱스를 생성한다 (없으면)."""
        try:
            cur = self._conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS drawings (
                    drawing_id      TEXT PRIMARY KEY,
                    file_path       TEXT    DEFAULT '',
                    file_name       TEXT    DEFAULT '',
                    category        TEXT    DEFAULT '',
                    ocr_text        TEXT    DEFAULT '',
                    part_numbers    TEXT    DEFAULT '[]',
                    dimensions      TEXT    DEFAULT '[]',
                    materials       TEXT    DEFAULT '[]',
                    description     TEXT    DEFAULT '',
                    metadata        TEXT    DEFAULT '{}',
                    yolo_confidence REAL    DEFAULT 0.0,
                    yolo_needs_review INTEGER DEFAULT 0,
                    yolo_top_k      TEXT    DEFAULT '[]',
                    detected_regions TEXT   DEFAULT '[]',
                    title_block_data TEXT   DEFAULT '{}',
                    parts_table_data TEXT   DEFAULT '{}',
                    detection_enhanced INTEGER DEFAULT 0,
                    dxf_path        TEXT    DEFAULT '',
                    similar_drawings TEXT   DEFAULT '[]',
                    registered_at   TEXT    DEFAULT '',
                    revision        INTEGER DEFAULT 1,
                    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_category ON drawings(category)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_file_name ON drawings(file_name)"
            )
            self._conn.commit()
        except sqlite3.Error as e:
            logger.error(f"DB 초기화 실패: {e}")
            raise

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------

    def _serialize_record(self, record_data: dict) -> dict:
        """파이썬 딕트를 SQLite 저장용으로 변환한다 (리스트/딕트 → JSON 문자열)."""
        row = {}
        for key, value in record_data.items():
            if key in self._JSON_COLUMNS:
                row[key] = json.dumps(value, ensure_ascii=False) if value is not None else "[]"
            elif key == "yolo_needs_review" or key == "detection_enhanced":
                row[key] = int(bool(value))
            else:
                row[key] = value
        return row

    def _deserialize_row(self, row: sqlite3.Row) -> dict:
        """SQLite Row를 파이썬 딕트로 변환한다 (JSON 문자열 → 리스트/딕트)."""
        data = dict(row)
        for col in self._JSON_COLUMNS:
            if col in data and isinstance(data[col], str):
                try:
                    data[col] = json.loads(data[col])
                except (json.JSONDecodeError, TypeError):
                    data[col] = [] if col != "metadata" and col != "title_block_data" and col != "parts_table_data" else {}
        # bool 복원
        if "yolo_needs_review" in data:
            data["yolo_needs_review"] = bool(data["yolo_needs_review"])
        if "detection_enhanced" in data:
            data["detection_enhanced"] = bool(data["detection_enhanced"])
        # created_at은 내부 관리용 → 외부 딕트에서 제거
        data.pop("created_at", None)
        return data

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(self, drawing_id: str, record_data: dict) -> None:
        """레코드를 추가/업데이트한다 (UPSERT)."""
        record_data = dict(record_data)  # 원본 변경 방지
        record_data["drawing_id"] = drawing_id
        row = self._serialize_record(record_data)

        columns = list(row.keys())
        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join(columns)
        # UPSERT: 충돌 시 전체 업데이트
        update_clause = ", ".join(
            f"{c} = excluded.{c}" for c in columns if c != "drawing_id"
        )
        sql = (
            f"INSERT INTO drawings ({col_names}) VALUES ({placeholders}) "
            f"ON CONFLICT(drawing_id) DO UPDATE SET {update_clause}"
        )
        try:
            self._conn.execute(sql, list(row.values()))
            self._conn.commit()
        except sqlite3.Error as e:
            logger.error(f"레코드 추가 실패 [{drawing_id}]: {e}")
            self._conn.rollback()

    def add_batch(self, records: dict[str, dict], batch_size: int = 1000) -> int:
        """여러 레코드를 배치 삽입한다.

        Args:
            records: {drawing_id: record_data, ...}
            batch_size: 커밋 단위

        Returns:
            삽입된 레코드 수
        """
        count = 0
        items = list(records.items())
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            try:
                for drawing_id, record_data in batch:
                    record_data = dict(record_data)
                    record_data["drawing_id"] = drawing_id
                    row = self._serialize_record(record_data)

                    columns = list(row.keys())
                    placeholders = ", ".join(["?"] * len(columns))
                    col_names = ", ".join(columns)
                    update_clause = ", ".join(
                        f"{c} = excluded.{c}" for c in columns if c != "drawing_id"
                    )
                    sql = (
                        f"INSERT INTO drawings ({col_names}) VALUES ({placeholders}) "
                        f"ON CONFLICT(drawing_id) DO UPDATE SET {update_clause}"
                    )
                    self._conn.execute(sql, list(row.values()))
                    count += 1
                self._conn.commit()
                logger.debug(f"배치 커밋: {min(i + batch_size, len(items))}/{len(items)}")
            except sqlite3.Error as e:
                logger.error(f"배치 삽입 실패 (offset={i}): {e}")
                self._conn.rollback()
        return count

    def get(self, drawing_id: str) -> dict | None:
        """drawing_id로 레코드를 조회한다."""
        try:
            cur = self._conn.execute(
                "SELECT * FROM drawings WHERE drawing_id = ?", (drawing_id,)
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._deserialize_row(row)
        except sqlite3.Error as e:
            logger.error(f"레코드 조회 실패 [{drawing_id}]: {e}")
            return None

    def get_all(self) -> dict[str, dict]:
        """모든 레코드를 반환한다. {drawing_id: record_data}"""
        try:
            cur = self._conn.execute("SELECT * FROM drawings")
            result: dict[str, dict] = {}
            for row in cur.fetchall():
                data = self._deserialize_row(row)
                result[data["drawing_id"]] = data
            return result
        except sqlite3.Error as e:
            logger.error(f"전체 레코드 조회 실패: {e}")
            return {}

    def delete(self, drawing_id: str) -> bool:
        """레코드를 삭제한다."""
        try:
            cur = self._conn.execute(
                "DELETE FROM drawings WHERE drawing_id = ?", (drawing_id,)
            )
            self._conn.commit()
            deleted = cur.rowcount > 0
            if deleted:
                logger.debug(f"레코드 삭제: {drawing_id}")
            return deleted
        except sqlite3.Error as e:
            logger.error(f"레코드 삭제 실패 [{drawing_id}]: {e}")
            self._conn.rollback()
            return False

    # ------------------------------------------------------------------
    # 검색
    # ------------------------------------------------------------------

    def search_by_part_number(self, part_number: str) -> list[dict]:
        """부품번호로 검색한다 (LIKE 검색, JSON 배열 내부)."""
        query = part_number.strip()
        if not query:
            return []
        try:
            cur = self._conn.execute(
                "SELECT * FROM drawings WHERE part_numbers LIKE ?",
                (f"%{query}%",),
            )
            return [self._deserialize_row(row) for row in cur.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"부품번호 검색 실패 [{part_number}]: {e}")
            return []

    def search_by_category(self, category: str) -> list[dict]:
        """카테고리로 검색한다 (정확 일치)."""
        try:
            cur = self._conn.execute(
                "SELECT * FROM drawings WHERE category = ?", (category,)
            )
            return [self._deserialize_row(row) for row in cur.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"카테고리 검색 실패 [{category}]: {e}")
            return []

    # ------------------------------------------------------------------
    # 집계 / 인덱스
    # ------------------------------------------------------------------

    def get_categories(self) -> list[str]:
        """전체 카테고리 목록을 반환한다 (중복 제거, 정렬)."""
        try:
            cur = self._conn.execute(
                "SELECT DISTINCT category FROM drawings WHERE category != '' ORDER BY category"
            )
            return [row[0] for row in cur.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"카테고리 목록 조회 실패: {e}")
            return []

    def count(self) -> int:
        """총 레코드 수를 반환한다."""
        try:
            cur = self._conn.execute("SELECT COUNT(*) FROM drawings")
            return cur.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"레코드 수 조회 실패: {e}")
            return 0

    def get_version_index(self) -> dict[str, list[str]]:
        """part_number -> [drawing_id, ...] 인덱스를 반환한다.

        part_numbers는 JSON 배열로 저장되므로 모든 행을 순회한다.
        """
        try:
            cur = self._conn.execute(
                "SELECT drawing_id, part_numbers, registered_at FROM drawings"
            )
            index: dict[str, list[tuple[str, str]]] = {}
            for row in cur.fetchall():
                drawing_id = row[0]
                registered_at = row[2] or ""
                try:
                    pns = json.loads(row[1]) if isinstance(row[1], str) else (row[1] or [])
                except (json.JSONDecodeError, TypeError):
                    pns = []
                for pn in pns:
                    if pn:
                        index.setdefault(pn, []).append((drawing_id, registered_at))
            # 등록 시간순 정렬 후 drawing_id만 반환
            result: dict[str, list[str]] = {}
            for pn, items in index.items():
                items.sort(key=lambda x: x[1])
                result[pn] = [did for did, _ in items]
            return result
        except sqlite3.Error as e:
            logger.error(f"버전 인덱스 생성 실패: {e}")
            return {}

    # ------------------------------------------------------------------
    # 연결 관리
    # ------------------------------------------------------------------

    def close(self) -> None:
        """DB 연결을 닫는다."""
        try:
            self._conn.close()
            logger.debug("RecordStore DB 연결 닫힘")
        except sqlite3.Error as e:
            logger.error(f"DB 연결 닫기 실패: {e}")

    def __del__(self):
        try:
            self._conn.close()
        except Exception:
            pass
