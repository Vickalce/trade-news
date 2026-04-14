from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.db.base import Base
from api.db.models import AlertLog, Recommendation
from api.schemas import NormalizedNewsEvent, ReactionFeatures
from api.services import pipeline



def _build_test_db():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()



def test_pipeline_end_to_end(monkeypatch):
    db = _build_test_db()

    sample_event = NormalizedNewsEvent(
        event_time_utc=datetime.now(timezone.utc),
        source="https://example.com/feed",
        headline="Apple earnings beat estimates as cloud revenue rises",
        body="AAPL jumps after strong guidance.",
        url="https://example.com/news/1",
        language="en",
        category="earnings",
        dedupe_hash="abc123hash",
    )

    monkeypatch.setattr(pipeline, "collect_events", lambda: [sample_event])
    monkeypatch.setattr(
        pipeline,
        "build_reaction_features",
        lambda symbol, headline: ReactionFeatures(
            symbol=symbol,
            last_price=110.0,
            volume=200000.0,
            volatility_proxy=0.02,
            baseline_price=100.0,
            baseline_volume=100000.0,
        ),
    )
    monkeypatch.setattr(pipeline, "deliver_alerts", lambda payload, channels: {channel: "delivered" for channel in channels})
    monkeypatch.setattr(pipeline.settings, "alert_channels_csv", "email,discord")
    monkeypatch.setattr(pipeline.settings, "kill_switch_enabled", False)
    monkeypatch.setattr(pipeline.settings, "enable_live_market_data", False)

    ingest_result = pipeline.run_ingestion_only(db)
    assert ingest_result["ingested"] == 1
    assert ingest_result["duplicates"] == 0

    results = pipeline.run_signal_pipeline(db, limit=10)
    assert len(results) == 1
    assert results[0].symbol == "AAPL"

    recommendations = db.query(Recommendation).all()
    alerts = db.query(AlertLog).all()
    assert len(recommendations) == 1
    assert len(alerts) == 2
