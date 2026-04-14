import hashlib
from datetime import datetime, timezone

from api.db.models import MarketSnapshot
from api.schemas import ReactionFeatures



def _stable_int(seed: str, modulo: int) -> int:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % modulo



def build_reaction_features(symbol: str, headline: str) -> ReactionFeatures:
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
