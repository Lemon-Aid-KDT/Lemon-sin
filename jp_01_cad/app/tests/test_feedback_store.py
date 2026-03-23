"""FeedbackStore 단위 테스트.

SQLite 기반 피드백 CRUD, 통계, 내보내기 기능을 검증한다.
"""

import csv
import json
import tempfile
from pathlib import Path

import pytest

from core.feedback_store import FeedbackStore


@pytest.fixture()
def store(tmp_path):
    """임시 DB를 사용하는 FeedbackStore."""
    db_path = tmp_path / "test_feedback.db"
    s = FeedbackStore(db_path=str(db_path))
    yield s
    s.close()


@pytest.fixture()
def populated_store(store):
    """테스트 데이터가 포함된 FeedbackStore."""
    store.add_feedback("shaft bearing", "text", "d001", 0.85, 1, category="bearing")
    store.add_feedback("shaft bearing", "text", "d002", 0.60, 0, category="bearing")
    store.add_feedback("shaft bearing", "text", "d003", 0.45, 1, category="bearing")
    store.add_feedback("gasket seal", "text", "d010", 0.90, 1, category="gasket")
    store.add_feedback("gasket seal", "text", "d011", 0.30, 0, category="gasket")
    store.add_feedback("bolt M10", "image", "d020", 0.70, -1, category="bolt")
    return store


# ─── TestCRUD ───


class TestCRUD:
    """피드백 추가 및 조회 테스트."""

    def test_add_feedback_returns_id(self, store):
        fid = store.add_feedback("query1", "text", "d001", 0.9, 1)
        assert isinstance(fid, int)
        assert fid >= 1

    def test_add_feedback_increments_id(self, store):
        fid1 = store.add_feedback("q1", "text", "d1", 0.5, 1)
        fid2 = store.add_feedback("q2", "text", "d2", 0.3, 0)
        assert fid2 > fid1

    def test_get_recent_returns_latest_first(self, populated_store):
        recent = populated_store.get_recent(limit=3)
        assert len(recent) == 3
        # 가장 마지막에 삽입된 것이 첫 번째
        assert recent[0]["drawing_id"] == "d020"

    def test_get_recent_limit(self, populated_store):
        recent = populated_store.get_recent(limit=2)
        assert len(recent) == 2

    def test_get_recent_all(self, populated_store):
        recent = populated_store.get_recent(limit=100)
        assert len(recent) == 6


# ─── TestStats ───


class TestStats:
    """피드백 통계 테스트."""

    def test_stats_counts(self, populated_store):
        stats = populated_store.get_feedback_stats()
        assert stats["total"] == 6
        assert stats["relevant"] == 3
        assert stats["irrelevant"] == 2
        assert stats["not_rated"] == 1

    def test_stats_by_category(self, populated_store):
        stats = populated_store.get_feedback_stats()
        by_cat = stats["by_category"]
        assert "bearing" in by_cat
        assert by_cat["bearing"]["total"] == 3
        assert by_cat["bearing"]["relevant"] == 2
        assert by_cat["bearing"]["irrelevant"] == 1

    def test_stats_empty_db(self, store):
        stats = store.get_feedback_stats()
        assert stats["total"] == 0
        assert stats["relevant"] == 0
        assert stats["irrelevant"] == 0
        assert stats["by_category"] == {}


# ─── TestExport ───


class TestExport:
    """내보내기 테스트."""

    def test_export_jsonl_creates_file(self, populated_store, tmp_path):
        out = tmp_path / "pairs.jsonl"
        path = populated_store.export_training_pairs(str(out))
        assert Path(path).exists()
        assert Path(path).stat().st_size > 0

    def test_export_jsonl_format(self, populated_store, tmp_path):
        out = tmp_path / "pairs.jsonl"
        populated_store.export_training_pairs(str(out))
        lines = out.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) >= 1
        for line in lines:
            obj = json.loads(line)
            assert "query" in obj
            assert "positive" in obj
            assert "negative" in obj

    def test_export_jsonl_training_pairs_content(self, populated_store, tmp_path):
        out = tmp_path / "pairs.jsonl"
        populated_store.export_training_pairs(str(out))
        lines = out.read_text(encoding="utf-8").strip().split("\n")
        pairs = [json.loads(l) for l in lines]
        # "shaft bearing" has 2 positives (d001, d003) and 1 negative (d002)
        shaft_pairs = [p for p in pairs if p["query"] == "shaft bearing"]
        assert len(shaft_pairs) == 2  # 2 positives x 1 negative
        assert all(p["negative"] == "d002" for p in shaft_pairs)

    def test_export_csv_creates_file(self, populated_store, tmp_path):
        out = tmp_path / "feedback.csv"
        path = populated_store.export_csv(str(out))
        assert Path(path).exists()

    def test_export_csv_format(self, populated_store, tmp_path):
        out = tmp_path / "feedback.csv"
        populated_store.export_csv(str(out))
        with open(out, encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            assert "query_text" in header
            assert "relevance" in header
            rows = list(reader)
            assert len(rows) == 6

    def test_export_default_path(self, populated_store):
        """output_path를 지정하지 않으면 data/ 디렉토리에 자동 생성."""
        path = populated_store.export_csv()
        assert Path(path).exists()
        Path(path).unlink(missing_ok=True)  # cleanup


# ─── TestEdgeCases ───


class TestEdgeCases:
    """엣지 케이스 테스트."""

    def test_empty_db_export_jsonl(self, store, tmp_path):
        out = tmp_path / "empty.jsonl"
        path = store.export_training_pairs(str(out))
        assert Path(path).exists()
        content = Path(path).read_text()
        assert content.strip() == ""

    def test_empty_db_export_csv(self, store, tmp_path):
        out = tmp_path / "empty.csv"
        path = store.export_csv(str(out))
        assert Path(path).exists()
        with open(out, encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)
            assert len(rows) == 0

    def test_duplicate_feedback_allowed(self, store):
        """동일 쿼리+도면에 대해 중복 피드백 허용."""
        fid1 = store.add_feedback("q", "text", "d1", 0.5, 1)
        fid2 = store.add_feedback("q", "text", "d1", 0.5, 0)
        assert fid2 > fid1
        recent = store.get_recent()
        assert len(recent) == 2

    def test_feedback_with_comment(self, store):
        fid = store.add_feedback(
            "q", "text", "d1", 0.5, 1, comment="매우 정확한 결과"
        )
        recent = store.get_recent(limit=1)
        assert recent[0]["user_comment"] == "매우 정확한 결과"

    def test_export_no_pairs_when_only_positives(self, store, tmp_path):
        """positive만 있고 negative가 없으면 쌍이 생성되지 않는다."""
        store.add_feedback("q", "text", "d1", 0.9, 1)
        store.add_feedback("q", "text", "d2", 0.8, 1)
        out = tmp_path / "no_pairs.jsonl"
        store.export_training_pairs(str(out))
        content = out.read_text().strip()
        assert content == ""
