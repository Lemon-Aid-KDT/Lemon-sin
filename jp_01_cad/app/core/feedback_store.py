"""사용자 피드백 저장소

검색 결과에 대한 사용자 평가(관련/무관)를 저장하고,
fine-tuning 데이터로 내보내는 기능을 제공한다.
"""

import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from loguru import logger


class FeedbackStore:
    """SQLite 기반 사용자 피드백 저장소.

    WAL 모드를 사용하여 동시 읽기/쓰기 성능을 보장한다.
    """

    def __init__(self, db_path: str = "data/feedback.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """SQLite 연결을 반환한다 (lazy init)."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _init_db(self) -> None:
        """피드백 테이블을 생성한다."""
        conn = self._get_conn()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_text TEXT,
                query_type TEXT DEFAULT 'text',
                drawing_id TEXT,
                score REAL,
                relevance INTEGER,
                category TEXT DEFAULT '',
                user_comment TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        logger.debug(f"FeedbackStore 초기화 완료: {self.db_path}")

    def add_feedback(
        self,
        query_text: str,
        query_type: str,
        drawing_id: str,
        score: float,
        relevance: int,
        category: str = "",
        comment: str = "",
    ) -> int:
        """피드백을 저장한다.

        Args:
            query_text: 검색 쿼리 텍스트
            query_type: 검색 유형 (text, image, dxf)
            drawing_id: 도면 ID
            score: 검색 유사도 점수
            relevance: 관련성 (1=relevant, 0=irrelevant, -1=not rated)
            category: 도면 카테고리
            comment: 사용자 코멘트

        Returns:
            생성된 feedback_id
        """
        conn = self._get_conn()
        cursor = conn.execute(
            """
            INSERT INTO feedback (query_text, query_type, drawing_id, score,
                                  relevance, category, user_comment)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (query_text, query_type, drawing_id, score, relevance, category, comment),
        )
        conn.commit()
        feedback_id = cursor.lastrowid
        logger.debug(
            f"피드백 저장: id={feedback_id}, query={query_text!r}, "
            f"drawing={drawing_id}, relevance={relevance}"
        )
        return feedback_id

    def get_feedback_stats(self) -> dict:
        """피드백 통계를 반환한다.

        Returns:
            {total, relevant, irrelevant, not_rated, by_category}
        """
        conn = self._get_conn()

        total = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
        relevant = conn.execute(
            "SELECT COUNT(*) FROM feedback WHERE relevance = 1"
        ).fetchone()[0]
        irrelevant = conn.execute(
            "SELECT COUNT(*) FROM feedback WHERE relevance = 0"
        ).fetchone()[0]
        not_rated = conn.execute(
            "SELECT COUNT(*) FROM feedback WHERE relevance = -1"
        ).fetchone()[0]

        # 카테고리별 통계
        rows = conn.execute(
            """
            SELECT category, COUNT(*) as cnt,
                   SUM(CASE WHEN relevance = 1 THEN 1 ELSE 0 END) as pos,
                   SUM(CASE WHEN relevance = 0 THEN 1 ELSE 0 END) as neg
            FROM feedback
            WHERE category != ''
            GROUP BY category
            ORDER BY cnt DESC
            """
        ).fetchall()

        by_category = {}
        for row in rows:
            by_category[row["category"]] = {
                "total": row["cnt"],
                "relevant": row["pos"],
                "irrelevant": row["neg"],
            }

        return {
            "total": total,
            "relevant": relevant,
            "irrelevant": irrelevant,
            "not_rated": not_rated,
            "by_category": by_category,
        }

    def export_training_pairs(self, output_path: str = "") -> str:
        """fine-tuning용 학습 데이터를 내보낸다.

        포맷: JSON Lines
        {"query": "shaft bearing", "positive": "drawing_id_1", "negative": "drawing_id_2"}

        relevant=1인 결과는 positive, relevant=0인 결과는 negative.
        같은 query_text에 대해 positive/negative 쌍을 생성한다.

        Returns:
            출력 파일 경로
        """
        if not output_path:
            output_path = str(
                self.db_path.parent / f"training_pairs_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
            )

        conn = self._get_conn()

        # 쿼리별 positive/negative 그룹핑
        rows = conn.execute(
            """
            SELECT query_text, drawing_id, relevance
            FROM feedback
            WHERE relevance IN (0, 1)
            ORDER BY query_text
            """
        ).fetchall()

        query_groups: dict[str, dict[str, list[str]]] = {}
        for row in rows:
            qt = row["query_text"]
            if qt not in query_groups:
                query_groups[qt] = {"positive": [], "negative": []}
            if row["relevance"] == 1:
                query_groups[qt]["positive"].append(row["drawing_id"])
            else:
                query_groups[qt]["negative"].append(row["drawing_id"])

        # 쌍 생성
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        pair_count = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for query_text, groups in query_groups.items():
                positives = groups["positive"]
                negatives = groups["negative"]
                if not positives or not negatives:
                    continue
                for pos in positives:
                    for neg in negatives:
                        line = json.dumps(
                            {"query": query_text, "positive": pos, "negative": neg},
                            ensure_ascii=False,
                        )
                        f.write(line + "\n")
                        pair_count += 1

        logger.info(f"학습 쌍 {pair_count}개 내보내기 완료: {output_path}")
        return output_path

    def export_csv(self, output_path: str = "") -> str:
        """전체 피드백을 CSV로 내보낸다.

        Returns:
            출력 파일 경로
        """
        if not output_path:
            output_path = str(
                self.db_path.parent / f"feedback_{datetime.now():%Y%m%d_%H%M%S}.csv"
            )

        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM feedback ORDER BY created_at DESC"
        ).fetchall()

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "query_text", "query_type", "drawing_id",
                "score", "relevance", "category", "user_comment", "created_at",
            ])
            for row in rows:
                writer.writerow([
                    row["id"], row["query_text"], row["query_type"],
                    row["drawing_id"], row["score"], row["relevance"],
                    row["category"], row["user_comment"], row["created_at"],
                ])

        logger.info(f"CSV 내보내기 완료 ({len(rows)}건): {output_path}")
        return output_path

    def get_recent(self, limit: int = 50) -> list[dict]:
        """최근 피드백 목록을 반환한다.

        Args:
            limit: 반환할 최대 건수

        Returns:
            피드백 딕셔너리 목록 (최신순)
        """
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM feedback ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()

        return [dict(row) for row in rows]

    def close(self) -> None:
        """DB 연결을 닫는다."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
