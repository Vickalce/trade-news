from datetime import datetime, timezone

from sqlalchemy import Select, desc, func, select
from sqlalchemy.orm import Session

from api.db.models import AlertLog, EventEntity, EventScore, NewsEvent, Recommendation
from api.schemas import ExtractedEntity, EventScoreInput, NormalizedNewsEvent


def get_recent_events(db: Session, limit: int = 50) -> list[NewsEvent]:
    stmt: Select[tuple[NewsEvent]] = select(NewsEvent).order_by(desc(NewsEvent.event_time_utc)).limit(limit)
    return list(db.scalars(stmt))


def get_event_by_dedupe_hash(db: Session, dedupe_hash: str) -> NewsEvent | None:
    stmt: Select[tuple[NewsEvent]] = select(NewsEvent).where(NewsEvent.dedupe_hash == dedupe_hash)
    return db.scalar(stmt)


def create_event(db: Session, event: NormalizedNewsEvent) -> NewsEvent:
    model = NewsEvent(**event.model_dump())
    db.add(model)
    db.flush()
    return model


def replace_entities(db: Session, event_id: int, entities: list[ExtractedEntity]) -> None:
    db.query(EventEntity).filter(EventEntity.event_id == event_id).delete()
    for entity in entities:
        db.add(
            EventEntity(
                event_id=event_id,
                entity_type=entity.entity_type,
                entity_value=entity.entity_value,
                confidence=entity.confidence,
            )
        )


def upsert_event_score(db: Session, event_id: int, score_input: EventScoreInput, final_score: float) -> EventScore:
    row = db.query(EventScore).filter(EventScore.event_id == event_id).one_or_none()
    payload = score_input.model_dump()
    if row is None:
        row = EventScore(event_id=event_id, final_score=final_score, **payload)
        db.add(row)
    else:
        row.relevance_score = score_input.relevance_score
        row.reaction_score = score_input.reaction_score
        row.historical_similarity_score = score_input.historical_similarity_score
        row.source_quality_score = score_input.source_quality_score
        row.final_score = final_score
        row.impact_horizon = score_input.impact_horizon
        row.scope_type = score_input.scope_type
    db.flush()
    return row


def create_recommendation(
    db: Session,
    event_id: int,
    symbol: str,
    recommendation: str,
    confidence: float,
    rationale: str,
    invalidation_conditions: str,
) -> Recommendation:
    row = Recommendation(
        event_id=event_id,
        symbol=symbol,
        recommendation=recommendation,
        confidence=confidence,
        rationale=rationale,
        invalidation_conditions=invalidation_conditions,
        created_at_utc=datetime.now(timezone.utc),
    )
    db.add(row)
    db.flush()
    return row


def log_alert(db: Session, recommendation_id: int, alert_channel: str, priority: str, delivery_status: str) -> AlertLog:
    row = AlertLog(
        recommendation_id=recommendation_id,
        alert_channel=alert_channel,
        priority=priority,
        delivered_at_utc=datetime.now(timezone.utc),
        delivery_status=delivery_status,
    )
    db.add(row)
    db.flush()
    return row


def get_latest_recommendation_for_symbol(db: Session, symbol: str) -> Recommendation | None:
    stmt: Select[tuple[Recommendation]] = (
        select(Recommendation)
        .where(Recommendation.symbol == symbol)
        .order_by(desc(Recommendation.created_at_utc))
        .limit(1)
    )
    return db.scalar(stmt)


def count_alerts_since(db: Session, since_utc: datetime) -> int:
    stmt = select(func.count(AlertLog.id)).where(AlertLog.delivered_at_utc >= since_utc)
    return int(db.scalar(stmt) or 0)
