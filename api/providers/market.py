import hashlib
from typing import Protocol

import httpx

from api.core.config import settings
from api.schemas import ReactionFeatures


class MarketDataProvider(Protocol):
    def get_reaction_features(self, symbol: str, headline: str) -> ReactionFeatures:
        ...


class YahooMarketDataProvider:
    def get_reaction_features(self, symbol: str, headline: str) -> ReactionFeatures:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {"range": "1d", "interval": "1m"}
        with httpx.Client(timeout=settings.market_data_timeout_seconds) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
        payload = response.json()

        result = (payload.get("chart") or {}).get("result") or []
        if not result:
            raise ValueError("No market data result")

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
            raise ValueError("Invalid price baseline")

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


class DeterministicFallbackMarketProvider:
    @staticmethod
    def _stable_int(seed: str, modulo: int) -> int:
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % modulo

    def get_reaction_features(self, symbol: str, headline: str) -> ReactionFeatures:
        seed = f"{symbol}:{headline}"
        baseline_price = 50 + self._stable_int(seed + ":bp", 400)
        pct_move = (self._stable_int(seed + ":pm", 1201) - 600) / 10000
        last_price = round(baseline_price * (1 + pct_move), 2)

        baseline_volume = 100_000 + self._stable_int(seed + ":bv", 2_000_000)
        volume = baseline_volume * (1 + (self._stable_int(seed + ":vs", 700) / 1000))
        volatility_proxy = round(0.01 + (self._stable_int(seed + ":vol", 500) / 10000), 4)

        return ReactionFeatures(
            symbol=symbol,
            last_price=float(last_price),
            volume=float(round(volume)),
            volatility_proxy=float(volatility_proxy),
            baseline_price=float(baseline_price),
            baseline_volume=float(baseline_volume),
        )



def get_market_data_provider() -> MarketDataProvider:
    if settings.market_data_provider == "fallback":
        return DeterministicFallbackMarketProvider()
    return YahooMarketDataProvider()
