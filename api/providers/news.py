from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
from typing import Protocol
import xml.etree.ElementTree as ET

import httpx

from api.core.config import settings
from api.providers.registry import NEWS_PROVIDER_REGISTRY, ProviderCapabilities, ProviderDefinition
from api.schemas import NormalizedNewsEvent
from api.services.classification import classify_category

DEFAULT_FEEDS = [
    "https://feeds.reuters.com/reuters/businessNews",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://feeds.marketwatch.com/marketwatch/topstories/",
]


class NewsProvider(Protocol):
    def collect_events(self) -> list[NormalizedNewsEvent]:
        ...


class RssNewsProvider:
    def __init__(self, feed_urls: list[str] | None = None):
        self.feed_urls = feed_urls or DEFAULT_FEEDS

    def collect_events(self) -> list[NormalizedNewsEvent]:
        events: list[NormalizedNewsEvent] = []
        for feed_url in self.feed_urls:
            try:
                events.extend(self._fetch_feed_events(feed_url))
            except Exception:
                continue
        return events

    def _fetch_feed_events(self, feed_url: str) -> list[NormalizedNewsEvent]:
        with httpx.Client(timeout=settings.news_timeout_seconds, follow_redirects=True) as client:
            response = client.get(feed_url)
            response.raise_for_status()

        root = ET.fromstring(response.text)
        items = root.findall("./channel/item")
        parsed: list[NormalizedNewsEvent] = []
        for item in items[: settings.max_feed_items_per_source]:
            record = self._parse_item(item, feed_url)
            if record is not None:
                parsed.append(record)
        return parsed

    @staticmethod
    def _parse_item(item: ET.Element, source_url: str) -> NormalizedNewsEvent | None:
        title = (item.findtext("title") or "").strip()
        if not title:
            return None

        link = (item.findtext("link") or "").strip() or None
        description = (item.findtext("description") or "").strip() or None
        pub_date_raw = (item.findtext("pubDate") or "").strip()

        event_time = datetime.now(timezone.utc)
        if pub_date_raw:
            try:
                event_time = parsedate_to_datetime(pub_date_raw).astimezone(timezone.utc)
            except (TypeError, ValueError, OverflowError):
                pass

        category = classify_category(f"{title} {description or ''}")
        dedupe_seed = f"{title.lower()}|{source_url}|{event_time.strftime('%Y-%m-%d %H:%M')}"
        dedupe_hash = hashlib.sha256(dedupe_seed.encode("utf-8")).hexdigest()[:64]

        return NormalizedNewsEvent(
            event_time_utc=event_time,
            source=source_url[:100],
            headline=title[:500],
            body=description,
            url=link[:1000] if link else None,
            language="en",
            category=category,
            dedupe_hash=dedupe_hash,
        )


class DemoNewsProvider:
    def collect_events(self) -> list[NormalizedNewsEvent]:
        now = datetime.now(timezone.utc)
        seed = f"demo:{now.strftime('%Y-%m-%d %H:%M')}"
        dedupe = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:64]
        return [
            NormalizedNewsEvent(
                event_time_utc=now,
                source="demo",
                headline="Apple and Microsoft lead AI earnings momentum",
                body="Demo feed event for local development.",
                url=None,
                language="en",
                category="earnings",
                dedupe_hash=dedupe,
            )
        ]


class FinnhubNewsProvider:
    def collect_events(self) -> list[NormalizedNewsEvent]:
        if not settings.finnhub_api_key:
            raise ValueError("FINNHUB_API_KEY is required for Finnhub news provider")

        params = {
            "category": settings.finnhub_news_category,
            "token": settings.finnhub_api_key,
        }
        endpoint = f"{settings.finnhub_base_url}/news"
        with httpx.Client(timeout=settings.news_timeout_seconds) as client:
            response = client.get(endpoint, params=params)
            response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            return []

        events: list[NormalizedNewsEvent] = []
        for item in payload[: settings.max_feed_items_per_source]:
            if not isinstance(item, dict):
                continue

            headline = str(item.get("headline") or "").strip()
            if not headline:
                continue

            summary = str(item.get("summary") or "").strip() or None
            source = str(item.get("source") or "finnhub").strip() or "finnhub"
            url = str(item.get("url") or "").strip() or None

            timestamp_raw = item.get("datetime")
            event_time = datetime.now(timezone.utc)
            if isinstance(timestamp_raw, (int, float)) and timestamp_raw > 0:
                event_time = datetime.fromtimestamp(timestamp_raw, tz=timezone.utc)

            category = classify_category(f"{headline} {summary or ''}")
            dedupe_seed = f"{headline.lower()}|{source.lower()}|{event_time.strftime('%Y-%m-%d %H:%M')}"
            dedupe_hash = hashlib.sha256(dedupe_seed.encode("utf-8")).hexdigest()[:64]

            events.append(
                NormalizedNewsEvent(
                    event_time_utc=event_time,
                    source=source[:100],
                    headline=headline[:500],
                    body=summary,
                    url=url[:1000] if url else None,
                    language="en",
                    category=category,
                    dedupe_hash=dedupe_hash,
                )
            )

        return events

NEWS_PROVIDER_REGISTRY.register(
    ProviderDefinition(
        key="rss",
        kind="news",
        display_name="RSS Feed Aggregator",
        description="Aggregates public RSS feeds from financial news publishers.",
        factory=RssNewsProvider,
        capabilities=ProviderCapabilities(
            auth_type="none",
            supports_news=True,
            notes="Best for public headlines; article structure varies by feed.",
        ),
    )
)

NEWS_PROVIDER_REGISTRY.register(
    ProviderDefinition(
        key="demo",
        kind="news",
        display_name="Demo News Provider",
        description="Returns deterministic sample headlines for local development.",
        factory=DemoNewsProvider,
        capabilities=ProviderCapabilities(
            auth_type="none",
            supports_news=True,
            notes="Development-only provider.",
        ),
    )
)

NEWS_PROVIDER_REGISTRY.register(
    ProviderDefinition(
        key="finnhub",
        kind="news",
        display_name="Finnhub News",
        description="Aggregates market news from Finnhub's news API.",
        factory=FinnhubNewsProvider,
        capabilities=ProviderCapabilities(
            auth_type="api_key",
            supports_news=True,
            notes="Use FINNHUB_API_KEY and optional FINNHUB_NEWS_CATEGORY.",
        ),
        config_keys=("finnhub_api_key",),
    )
)


def get_news_provider() -> NewsProvider:
    return NEWS_PROVIDER_REGISTRY.create(settings.news_provider)
