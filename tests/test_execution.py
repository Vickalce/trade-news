from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.core.config import settings
from api.db.base import Base
from api.db.models import Recommendation
from api.services.execution import build_order_from_recommendation, submit_order



def _db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()



def test_build_order_from_buy_recommendation(monkeypatch):
    monkeypatch.setattr(settings, "order_max_notional_usd", 5000.0)
    rec = Recommendation(
        event_id=1,
        symbol="AAPL",
        recommendation="buy_candidate",
        confidence=80,
        rationale="test",
        invalidation_conditions=None,
        created_at_utc=datetime.now(timezone.utc),
    )

    order = build_order_from_recommendation(rec, account_id="abc", price_hint=100)
    assert order.side == "BUY"
    assert order.quantity == 50



def test_hold_recommendation_is_not_executable():
    rec = Recommendation(
        event_id=1,
        symbol="AAPL",
        recommendation="hold",
        confidence=50,
        rationale="test",
        invalidation_conditions=None,
        created_at_utc=datetime.now(timezone.utc),
    )
    with pytest.raises(ValueError):
        build_order_from_recommendation(rec, account_id="abc", price_hint=100)



def test_submit_order_blocked_by_kill_switch(monkeypatch):
    monkeypatch.setattr(settings, "broker_kill_switch_enabled", True)
    monkeypatch.setattr(settings, "broker_dry_run", False)

    rec = Recommendation(
        event_id=1,
        symbol="AAPL",
        recommendation="buy_candidate",
        confidence=80,
        rationale="test",
        invalidation_conditions=None,
        created_at_utc=datetime.now(timezone.utc),
    )
    order = build_order_from_recommendation(rec, account_id="abc", price_hint=100)
    result = submit_order(order)
    assert result.status == "blocked"
