from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from api.core.config import settings
from api.db import crud
from api.schemas import EventScoreInput, PipelineResult
from api.services.alerts import deliver_alerts
from api.services.classification import classify_scope
from api.services.extraction import extract_entities
from api.services.ingestion import collect_events
from api.services.mapping import map_entities_to_symbols
from api.services.reaction import build_reaction_features, persist_snapshot
from api.services.recommendation import build_recommendation
from api.services.scoring import (
    compute_final_score,
    compute_historical_similarity,
    compute_reaction_score,
    compute_relevance_score,
    compute_source_quality,
)



def run_ingestion_only(db: Session) -> dict[str, int]:
    ingested = 0
    duplicates = 0
    for event in collect_events():
        if crud.get_event_by_dedupe_hash(db, event.dedupe_hash):
            duplicates += 1
            continue
        crud.create_event(db, event)
        ingested += 1
    db.commit()
    return {"ingested": ingested, "duplicates": duplicates}



def run_signal_pipeline(db: Session, limit: int = 20) -> list[PipelineResult]:
    results: list[PipelineResult] = []
    events = crud.get_recent_events(db, limit=limit)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    channels = [item.strip() for item in settings.alert_channels_csv.split(",") if item.strip()]
    if not channels:
        channels = ["email"]

    for event in events:
        entities = extract_entities(event.headline, event.body)
        crud.replace_entities(db, event.id, entities)

        mapping = map_entities_to_symbols(entities)
        symbol = (mapping.symbols or ["SPY"])[0]

        scope_type = classify_scope([entity.entity_type for entity in entities], event.category or "other")
        impact_horizon = "short" if scope_type == "security" else "medium"

        reaction = build_reaction_features(symbol, event.headline)
        persist_snapshot(db, reaction)

        score_input = EventScoreInput(
            relevance_score=compute_relevance_score(event.category or "other", scope_type),
            reaction_score=compute_reaction_score(
                reaction.last_price,
                reaction.baseline_price,
                reaction.volume,
                reaction.baseline_volume,
            ),
            historical_similarity_score=compute_historical_similarity(event.category or "other", len(entities)),
            source_quality_score=compute_source_quality(event.source),
            impact_horizon=impact_horizon,
            scope_type=scope_type,
        )
        final_score = compute_final_score(score_input)
        crud.upsert_event_score(db, event.id, score_input, final_score)

        recommendation, confidence, rationale, invalidation, priority = build_recommendation(
            final_score,
            reaction.last_price,
            reaction.baseline_price,
        )

        if confidence < settings.min_confidence_threshold:
            recommendation = "hold"
            priority = "low"
            rationale = f"Confidence {confidence} below threshold {settings.min_confidence_threshold}."

        latest_for_symbol = crud.get_latest_recommendation_for_symbol(db, symbol)
        if latest_for_symbol is not None:
            cooldown_cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.symbol_cooldown_minutes)
            created_at = latest_for_symbol.created_at_utc
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            in_cooldown = created_at >= cooldown_cutoff
            conflicting = latest_for_symbol.recommendation != recommendation and recommendation != "hold"
            if in_cooldown and conflicting:
                recommendation = "hold"
                priority = "low"
                rationale = "Conflicting signal in cooldown window. Guardrail forced hold."

        rec_row = crud.create_recommendation(
            db=db,
            event_id=event.id,
            symbol=symbol,
            recommendation=recommendation,
            confidence=confidence,
            rationale=rationale,
            invalidation_conditions=invalidation,
        )

        alerts_today = crud.count_alerts_since(db, today_start)
        delivery_statuses = {channel: "suppressed" for channel in channels}
        if not settings.kill_switch_enabled and alerts_today < settings.max_alerts_per_day:
            payload = f"{symbol} | {recommendation} | score={final_score} | {rationale}"
            delivery_statuses = deliver_alerts(payload, channels)
        for channel, status in delivery_statuses.items():
            crud.log_alert(
                db,
                recommendation_id=rec_row.id,
                alert_channel=channel,
                priority=priority,
                delivery_status=status,
            )

        results.append(
            PipelineResult(
                event_id=event.id,
                symbol=symbol,
                final_score=final_score,
                recommendation=recommendation,
                confidence=confidence,
                rationale=rationale,
                priority=priority,
            )
        )

    db.commit()
    return results
