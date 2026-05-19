"""add social login columns

Revision ID: 0001
Revises:
Create Date: 2026-05-13

"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # email, password_hash nullable 허용 (소셜 로그인 유저는 비밀번호 없음)
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=True)
    op.alter_column("users", "password_hash", existing_type=sa.Text(), nullable=True)

    # 소셜 로그인 ID 컬럼 추가
    op.add_column("users", sa.Column("google_id", sa.String(255), unique=True, nullable=True))
    op.add_column("users", sa.Column("kakao_id", sa.String(255), unique=True, nullable=True))


def downgrade() -> None:
    op.drop_column("users", "kakao_id")
    op.drop_column("users", "google_id")
    op.alter_column("users", "password_hash", existing_type=sa.Text(), nullable=False)
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=False)
