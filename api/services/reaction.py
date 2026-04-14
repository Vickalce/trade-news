import hashlib
from datetime import datetime, timezone

import httpx

from api.core.config import settings
from api.db.models import MarketSnapshot
from api.schemas import ReactionFeatures


def _stable_int(seed: str, modulo: int) -> int:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % modulo


def _fallback_reaction_features(symbol: str, headline: str) -> ReactionFeatures:
    seed = f"{symbol}:{headline}"
    baseline_price = 50 + _stable_int(seed + ":bp", 400)
    pct_move = (_stable_int(seed + ":pm", 1201) - 600) / 10000
    last_price = round(baseline_price * (1 + pct_move), 2)

    baseline_volume = 100_000 + _stable_int(seed + ":bv", 2_000_000)
    volume = baseline_volume * (1 + (_stable_int(seed + ":vs", 700) / 1000))
    volatility_proxy = round(0.01 + (_stable_int(seed + ":vol", 500) / 10000), 4)

    return ReactionFeatures(
        symbol=symbol,
        last_price=float(last_price),
        volume=float(round(volume)),
        volatility_proxy=float(volatility_proxy),
        baseline_price=float(baseline_price),
        baseline_volume=float(baseline_volume),
    )


def _fetch_live_quote(symbol: str) -> ReactionFeatures | None:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"range": "1d", "interval": "1m"}
    with httpx.Client(timeout=settings.market_data_timeout_seconds) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
    payload = response.json()

    result = (payload.get("chart") or {}).get("result") or []
    if not result:
        return None

    meta = result[0].get("meta") or {}
    indicators = result[0].get("indicators") or {}
    quote = (indicators.get("quote") or [{}])[0]
    volume_series = [value for value in (quote.get("volume") or []) if value is not None]

    last_price = float(meta.get("regularMarketPrice") or 0)
    baseline_price = float(meta.get("previousClose") or meta.get("chartPreviousClose") or 0)
    baseline_volume = float(meta.get("regularMarketVolume") or 0)
    if baseline_volume <= 0 and volume_series:
        baseline_volume = float(sum(volume_series) / len(volume_series))

    if last_price <= 0 or baseline_price <= 0:
        return None

    current_volume = float(volume_series[-1]) if volume_series else baseline_volume
    if current_volume <= 0:
        current_volume = baseline_volume

    volatility_proxy = abs(last_price - baseline_price) / baseline_price
    return ReactionFeatures(
        symbol=symbol,
        last_price=round(last_price, 4),
        volume=round(current_volume, 2),
        volatility_proxy=round(volatility_proxy, 6),
        baseline_price=round(baseline_price, 4),
        baseline_volume=round(max(1.0, baseline_volume), 2),
    )


def build_reaction_features(symbol: str, headline: str) -> ReactionFeatures:
    if settings.enable_live_market_data:
        try:
            live = _fetch_live_quote(symbol)
            if live is not None:
                return live
        except Exception:
            pass
    return _fallback_reaction_features(symbol, headline)


def persist_snapshot(db, reaction: ReactionFeatures) -> MarketSnapshot:
    snapshot = MarketSnapshot(
        symbol=reaction.symbol,
        snapshot_time_utc=datetime.now(timezone.utc),
        last_price=reaction.last_price,
        volume=reaction.volume,
        volatility_proxy=reaction.volatility_proxy,
        baseline_price=reaction.baseline_price,
        baseline_volume=reaction.baseline_volume,
    )
    db.add(snapshot)
    db.flush()
    return snapshot
