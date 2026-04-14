"""Initial schema

Revision ID: 20260413_0001
Revises:
Create Date: 2026-04-13

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260413_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "news_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("headline", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("dedupe_hash", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_news_events_event_time_utc", "news_events", ["event_time_utc"], unique=False)
    op.create_index("ix_news_events_source", "news_events", ["source"], unique=False)
    op.create_index("ix_news_events_category", "news_events", ["category"], unique=False)
    op.create_index("ix_news_events_dedupe_hash", "news_events", ["dedupe_hash"], unique=True)

    op.create_table(
        "event_entities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("news_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_value", sa.String(length=255), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
    )
    op.create_index("ix_event_entities_event_id", "event_entities", ["event_id"], unique=False)
    op.create_index("ix_event_entities_entity_type", "event_entities", ["entity_type"], unique=False)
    op.create_index("ix_event_entities_entity_value", "event_entities", ["entity_value"], unique=False)

    op.create_table(
        "market_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("snapshot_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_price", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.Column("volatility_proxy", sa.Float(), nullable=False),
        sa.Column("baseline_price", sa.Float(), nullable=False),
        sa.Column("baseline_volume", sa.Float(), nullable=False),
    )
    op.create_index("ix_market_snapshots_symbol", "market_snapshots", ["symbol"], unique=False)
    op.create_index("ix_market_snapshots_snapshot_time_utc", "market_snapshots", ["snapshot_time_utc"], unique=False)

    op.create_table(
        "event_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("news_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.Column("reaction_score", sa.Float(), nullable=False),
        sa.Column("historical_similarity_score", sa.Float(), nullable=True),
        sa.Column("source_quality_score", sa.Float(), nullable=True),
        sa.Column("final_score", sa.Float(), nullable=False),
        sa.Column("impact_horizon", sa.String(length=16), nullable=False),
        sa.Column("scope_type", sa.String(length=16), nullable=False),
    )
    op.create_index("ix_event_scores_event_id", "event_scores", ["event_id"], unique=True)

    op.create_table(
        "recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("news_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("recommendation", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("invalidation_conditions", sa.Text(), nullable=True),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_recommendations_event_id", "recommendations", ["event_id"], unique=False)
    op.create_index("ix_recommendations_symbol", "recommendations", ["symbol"], unique=False)
    op.create_index("ix_recommendations_recommendation", "recommendations", ["recommendation"], unique=False)
    op.create_index("ix_recommendations_created_at_utc", "recommendations", ["created_at_utc"], unique=False)
    op.create_index("ix_recommendations_event_symbol", "recommendations", ["event_id", "symbol"], unique=False)

    op.create_table(
        "alert_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recommendation_id", sa.Integer(), sa.ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alert_channel", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("delivered_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_status", sa.String(length=32), nullable=False),
    )
    op.create_index("ix_alert_log_recommendation_id", "alert_log", ["recommendation_id"], unique=False)
    op.create_index("ix_alert_log_priority", "alert_log", ["priority"], unique=False)
    op.create_index("ix_alert_log_delivered_at_utc", "alert_log", ["delivered_at_utc"], unique=False)
    op.create_index("ix_alert_log_delivery_status", "alert_log", ["delivery_status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_alert_log_delivery_status", table_name="alert_log")
    op.drop_index("ix_alert_log_delivered_at_utc", table_name="alert_log")
    op.drop_index("ix_alert_log_priority", table_name="alert_log")
    op.drop_index("ix_alert_log_recommendation_id", table_name="alert_log")
    op.drop_table("alert_log")

    op.drop_index("ix_recommendations_event_symbol", table_name="recommendations")
    op.drop_index("ix_recommendations_created_at_utc", table_name="recommendations")
    op.drop_index("ix_recommendations_recommendation", table_name="recommendations")
    op.drop_index("ix_recommendations_symbol", table_name="recommendations")
    op.drop_index("ix_recommendations_event_id", table_name="recommendations")
    op.drop_table("recommendations")

    op.drop_index("ix_event_scores_event_id", table_name="event_scores")
    op.drop_table("event_scores")

    op.drop_index("ix_market_snapshots_snapshot_time_utc", table_name="market_snapshots")
    op.drop_index("ix_market_snapshots_symbol", table_name="market_snapshots")
    op.drop_table("market_snapshots")

    op.drop_index("ix_event_entities_entity_value", table_name="event_entities")
    op.drop_index("ix_event_entities_entity_type", table_name="event_entities")
    op.drop_index("ix_event_entities_event_id", table_name="event_entities")
    op.drop_table("event_entities")

    op.drop_index("ix_news_events_dedupe_hash", table_name="news_events")
    op.drop_index("ix_news_events_category", table_name="news_events")
    op.drop_index("ix_news_events_source", table_name="news_events")
    op.drop_index("ix_news_events_event_time_utc", table_name="news_events")
    op.drop_table("news_events")
