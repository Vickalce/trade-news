"""Add event deduplication tracking

Revision ID: 20260414_0002
Revises: 20260413_0001
Create Date: 2026-04-14

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260414_0002"
down_revision: Union[str, Sequence[str], None] = "20260413_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("news_events", sa.Column("has_been_scored", sa.Boolean(), nullable=False, server_default="0"))
    op.create_index("ix_news_events_has_been_scored", "news_events", ["has_been_scored"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_news_events_has_been_scored", table_name="news_events")
    op.drop_column("news_events", "has_been_scored")
