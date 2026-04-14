from datetime import datetime, timezone

from api.core.config import settings
from api.db.models import MarketSnapshot
from api.providers.market import DeterministicFallbackMarketProvider, get_market_data_provider
from api.schemas import ReactionFeatures



def build_reaction_features(symbol: str, headline: str) -> ReactionFeatures:
    provider = get_market_data_provider()
    if settings.enable_live_market_data:
        try:
            return provider.get_reaction_features(symbol, headline)
        except Exception:
            pass
    fallback = DeterministicFallbackMarketProvider()
    return fallback.get_reaction_features(symbol, headline)



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
