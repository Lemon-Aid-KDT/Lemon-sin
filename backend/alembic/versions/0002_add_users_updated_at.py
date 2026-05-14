"""add users.updated_at

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-13

Reason: src/models/user.py 의 User 가 TimestampMixin 을 상속해서 updated_at 매핑을 요구하지만
init.sql 의 users 테이블에는 updated_at 컬럼이 없어 모든 ORM SELECT/INSERT 가 UndefinedColumn 으로 500.
"""

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "updated_at")
