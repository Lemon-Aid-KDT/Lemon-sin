"""RecordStore (SQLite) 테스트

core/record_store.py의 CRUD, 검색, 마이그레이션 기능을 검증한다.
"""

import json
import sqlite3
import pytest
from pathlib import Path

from core.record_store import RecordStore


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def db_path(tmp_path):
    """임시 SQLite DB 경로"""
    return str(tmp_path / "test_records.db")


@pytest.fixture
def store(db_path):
    """RecordStore 인스턴스"""
    s = RecordStore(db_path=db_path)
    yield s
    s.close()


@pytest.fixture
def sample_record():
    """테스트용 레코드 데이터"""
    return {
        "drawing_id": "abc12345",
        "file_path": "/data/drawings/shaft_01.png",
        "file_name": "shaft_01.png",
        "category": "Shafts",
        "ocr_text": "SH-1234 S45C Ø50mm",
        "part_numbers": ["SH-1234", "SH-1234-A"],
        "dimensions": ["Ø50mm", "100mm"],
        "materials": ["S45C"],
        "description": "A shaft drawing",
        "metadata": {"source": "MiSUMi", "page": 1},
        "yolo_confidence": 0.92,
        "yolo_needs_review": False,
        "yolo_top_k": [["Shafts", 0.92], ["Rods", 0.05]],
        "detected_regions": [{"class": "title_block", "confidence": 0.9}],
        "title_block_data": {"drawing_number": "SH-1234"},
        "parts_table_data": {},
        "detection_enhanced": True,
        "dxf_path": "/data/dxf/shaft_01.dxf",
        "similar_drawings": [],
        "registered_at": "2026-03-20T10:00:00",
        "revision": 1,
    }


@pytest.fixture
def sample_record_2():
    """두 번째 테스트용 레코드"""
    return {
        "drawing_id": "def67890",
        "file_path": "/data/drawings/gear_01.png",
        "file_name": "gear_01.png",
        "category": "Gears",
        "ocr_text": "GR-5678 SCM415",
        "part_numbers": ["GR-5678"],
        "dimensions": ["Ø80mm"],
        "materials": ["SCM415"],
        "description": "A gear drawing",
        "metadata": {},
        "yolo_confidence": 0.85,
        "yolo_needs_review": False,
        "dxf_path": "",
        "registered_at": "2026-03-20T11:00:00",
        "revision": 1,
    }


# ─────────────────────────────────────────────
# TestInit
# ─────────────────────────────────────────────

class TestInit:
    """DB 초기화 테스트"""

    def test_db_file_created(self, db_path):
        """DB 파일이 생성된다."""
        store = RecordStore(db_path=db_path)
        assert Path(db_path).exists()
        store.close()

    def test_table_exists(self, store, db_path):
        """drawings 테이블이 존재한다."""
        conn = sqlite3.connect(db_path)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='drawings'"
        )
        assert cur.fetchone() is not None
        conn.close()

    def test_wal_mode(self, store, db_path):
        """WAL 모드가 활성화된다."""
        conn = sqlite3.connect(db_path)
        cur = conn.execute("PRAGMA journal_mode")
        mode = cur.fetchone()[0]
        assert mode == "wal"
        conn.close()

    def test_indexes_exist(self, store, db_path):
        """category, file_name 인덱스가 존재한다."""
        conn = sqlite3.connect(db_path)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
        index_names = {row[0] for row in cur.fetchall()}
        assert "idx_category" in index_names
        assert "idx_file_name" in index_names
        conn.close()


# ─────────────────────────────────────────────
# TestCRUD
# ─────────────────────────────────────────────

class TestCRUD:
    """기본 CRUD 테스트"""

    def test_add_and_get(self, store, sample_record):
        """레코드 추가 후 조회한다."""
        store.add("abc12345", sample_record)
        result = store.get("abc12345")
        assert result is not None
        assert result["drawing_id"] == "abc12345"
        assert result["category"] == "Shafts"
        assert result["file_name"] == "shaft_01.png"

    def test_get_returns_none_for_missing(self, store):
        """존재하지 않는 ID는 None을 반환한다."""
        assert store.get("nonexistent") is None

    def test_json_fields_deserialized(self, store, sample_record):
        """JSON 컬럼이 올바르게 역직렬화된다."""
        store.add("abc12345", sample_record)
        result = store.get("abc12345")
        assert isinstance(result["part_numbers"], list)
        assert result["part_numbers"] == ["SH-1234", "SH-1234-A"]
        assert isinstance(result["metadata"], dict)
        assert result["metadata"]["source"] == "MiSUMi"
        assert isinstance(result["yolo_top_k"], list)

    def test_bool_fields_deserialized(self, store, sample_record):
        """bool 컬럼이 올바르게 역직렬화된다."""
        store.add("abc12345", sample_record)
        result = store.get("abc12345")
        assert result["yolo_needs_review"] is False
        assert result["detection_enhanced"] is True

    def test_get_all(self, store, sample_record, sample_record_2):
        """get_all()은 모든 레코드를 반환한다."""
        store.add("abc12345", sample_record)
        store.add("def67890", sample_record_2)
        all_records = store.get_all()
        assert len(all_records) == 2
        assert "abc12345" in all_records
        assert "def67890" in all_records

    def test_delete(self, store, sample_record):
        """레코드를 삭제한다."""
        store.add("abc12345", sample_record)
        assert store.delete("abc12345") is True
        assert store.get("abc12345") is None

    def test_delete_nonexistent(self, store):
        """존재하지 않는 레코드 삭제는 False를 반환한다."""
        assert store.delete("nonexistent") is False

    def test_count(self, store, sample_record, sample_record_2):
        """count()는 총 레코드 수를 반환한다."""
        assert store.count() == 0
        store.add("abc12345", sample_record)
        assert store.count() == 1
        store.add("def67890", sample_record_2)
        assert store.count() == 2

    def test_upsert(self, store, sample_record):
        """동일 ID로 추가하면 업데이트된다 (UPSERT)."""
        store.add("abc12345", sample_record)
        # 카테고리 변경
        updated = dict(sample_record)
        updated["category"] = "Rods"
        store.add("abc12345", updated)
        result = store.get("abc12345")
        assert result["category"] == "Rods"
        assert store.count() == 1  # 중복 없음


# ─────────────────────────────────────────────
# TestSearch
# ─────────────────────────────────────────────

class TestSearch:
    """검색 테스트"""

    def test_search_by_part_number(self, store, sample_record, sample_record_2):
        """부품번호 LIKE 검색한다."""
        store.add("abc12345", sample_record)
        store.add("def67890", sample_record_2)
        results = store.search_by_part_number("SH-1234")
        assert len(results) == 1
        assert results[0]["drawing_id"] == "abc12345"

    def test_search_by_part_number_partial(self, store, sample_record):
        """부품번호 부분 일치 검색한다."""
        store.add("abc12345", sample_record)
        results = store.search_by_part_number("SH-")
        assert len(results) == 1

    def test_search_by_part_number_empty(self, store):
        """빈 쿼리는 빈 목록을 반환한다."""
        assert store.search_by_part_number("") == []

    def test_search_by_category(self, store, sample_record, sample_record_2):
        """카테고리 검색한다."""
        store.add("abc12345", sample_record)
        store.add("def67890", sample_record_2)
        results = store.search_by_category("Shafts")
        assert len(results) == 1
        assert results[0]["drawing_id"] == "abc12345"

    def test_get_categories(self, store, sample_record, sample_record_2):
        """카테고리 목록을 반환한다."""
        store.add("abc12345", sample_record)
        store.add("def67890", sample_record_2)
        categories = store.get_categories()
        assert "Shafts" in categories
        assert "Gears" in categories
        assert len(categories) == 2


# ─────────────────────────────────────────────
# TestVersionIndex
# ─────────────────────────────────────────────

class TestVersionIndex:
    """버전 인덱스 테스트"""

    def test_version_index(self, store, sample_record, sample_record_2):
        """part_number -> [drawing_id, ...] 인덱스를 생성한다."""
        store.add("abc12345", sample_record)
        store.add("def67890", sample_record_2)
        index = store.get_version_index()
        assert "SH-1234" in index
        assert "abc12345" in index["SH-1234"]
        assert "GR-5678" in index
        assert "def67890" in index["GR-5678"]

    def test_version_index_multiple_parts(self, store, sample_record):
        """하나의 레코드에 여러 부품번호가 있을 때 각각 인덱싱된다."""
        store.add("abc12345", sample_record)
        index = store.get_version_index()
        # sample_record는 ["SH-1234", "SH-1234-A"] 2개
        assert "SH-1234" in index
        assert "SH-1234-A" in index

    def test_version_index_sorted_by_registered_at(self, store):
        """버전 인덱스는 등록 시간순으로 정렬된다."""
        rec_old = {
            "drawing_id": "old",
            "part_numbers": ["PN-001"],
            "registered_at": "2026-01-01T00:00:00",
        }
        rec_new = {
            "drawing_id": "new",
            "part_numbers": ["PN-001"],
            "registered_at": "2026-03-01T00:00:00",
        }
        store.add("old", rec_old)
        store.add("new", rec_new)
        index = store.get_version_index()
        assert index["PN-001"] == ["old", "new"]


# ─────────────────────────────────────────────
# TestMigration
# ─────────────────────────────────────────────

class TestMigration:
    """records.json -> SQLite 마이그레이션 라운드트립 테스트"""

    def test_json_to_sqlite_roundtrip(self, tmp_path, sample_record, sample_record_2):
        """records.json → SQLite → get_all 라운드트립."""
        # records.json 생성
        json_data = {
            "abc12345": sample_record,
            "def67890": sample_record_2,
        }
        json_file = tmp_path / "records.json"
        json_file.write_text(json.dumps(json_data, ensure_ascii=False), encoding="utf-8")

        # SQLite로 마이그레이션
        db_path = str(tmp_path / "records.db")
        store = RecordStore(db_path=db_path)

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        count = store.add_batch(data, batch_size=10)
        assert count == 2

        # 검증: 수 일치
        assert store.count() == 2

        # 검증: 필드 보존
        rec = store.get("abc12345")
        assert rec["category"] == "Shafts"
        assert rec["part_numbers"] == ["SH-1234", "SH-1234-A"]
        assert rec["materials"] == ["S45C"]
        assert rec["yolo_confidence"] == pytest.approx(0.92)

        store.close()


# ─────────────────────────────────────────────
# TestEdgeCases
# ─────────────────────────────────────────────

class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_empty_db(self, store):
        """빈 DB에서 get_all은 빈 딕트를 반환한다."""
        assert store.get_all() == {}
        assert store.count() == 0

    def test_add_minimal_record(self, store):
        """최소 필드만 있는 레코드를 추가할 수 있다."""
        store.add("min001", {"drawing_id": "min001", "file_name": "test.png"})
        result = store.get("min001")
        assert result is not None
        assert result["file_name"] == "test.png"
        assert result["category"] == ""  # 기본값

    def test_add_batch_empty(self, store):
        """빈 배치 삽입은 0을 반환한다."""
        count = store.add_batch({})
        assert count == 0

    def test_close_and_reopen(self, db_path, sample_record):
        """DB를 닫고 다시 열면 데이터가 유지된다."""
        store1 = RecordStore(db_path=db_path)
        store1.add("abc12345", sample_record)
        store1.close()

        store2 = RecordStore(db_path=db_path)
        result = store2.get("abc12345")
        assert result is not None
        assert result["category"] == "Shafts"
        store2.close()

    def test_special_characters_in_text(self, store):
        """특수문자가 포함된 텍스트를 처리할 수 있다."""
        rec = {
            "drawing_id": "sp001",
            "ocr_text": "도면번호: SH-1234 재질: S45C (경화처리) 'quoted' \"double\"",
            "description": "특수문자 테스트: <>&'\"",
        }
        store.add("sp001", rec)
        result = store.get("sp001")
        assert "도면번호" in result["ocr_text"]
        assert "<>&" in result["description"]
