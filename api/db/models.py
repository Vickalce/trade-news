from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from api.db.base import Base


class NewsEvent(Base):
    __tablename__ = "news_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_time_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str] = mapped_column(String(100), index=True)
    headline: Mapped[str] = mapped_column(String(500))
    body: Mapped[Optional[str]] = mapped_column(Text())
    url: Mapped[Optional[str]] = mapped_column(String(1000))
    language: Mapped[str] = mapped_column(String(16), default="en")
    category: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    dedupe_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    has_been_scored: Mapped[bool] = mapped_column(default=False, index=True)


class EventEntity(Base):
    __tablename__ = "event_entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("news_events.id", ondelete="CASCADE"), index=True)
    entity_type: Mapped[str] = mapped_column(String(32), index=True)
    entity_value: Mapped[str] = mapped_column(String(255), index=True)
    confidence: Mapped[float] = mapped_column(Float)


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    snapshot_time_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_price: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    volatility_proxy: Mapped[float] = mapped_column(Float)
    baseline_price: Mapped[float] = mapped_column(Float)
    baseline_volume: Mapped[float] = mapped_column(Float)


class EventScore(Base):
    __tablename__ = "event_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("news_events.id", ondelete="CASCADE"), unique=True, index=True)
    relevance_score: Mapped[float] = mapped_column(Float)
    reaction_score: Mapped[float] = mapped_column(Float)
    historical_similarity_score: Mapped[Optional[float]] = mapped_column(Float)
    source_quality_score: Mapped[Optional[float]] = mapped_column(Float)
    final_score: Mapped[float] = mapped_column(Float)
    impact_horizon: Mapped[str] = mapped_column(String(16))
    scope_type: Mapped[str] = mapped_column(String(16))


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("news_events.id", ondelete="CASCADE"), index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    recommendation: Mapped[str] = mapped_column(String(32), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    rationale: Mapped[str] = mapped_column(Text)
    invalidation_conditions: Mapped[Optional[str]] = mapped_column(Text)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AlertLog(Base):
    __tablename__ = "alert_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(ForeignKey("recommendations.id", ondelete="CASCADE"), index=True)
    alert_channel: Mapped[str] = mapped_column(String(32))
    priority: Mapped[str] = mapped_column(String(16), index=True)
    delivered_at_utc: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    delivery_status: Mapped[str] = mapped_column(String(32), index=True)


Index("ix_recommendations_event_symbol", Recommendation.event_id, Recommendation.symbol)
