import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET

import httpx

from api.schemas import NormalizedNewsEvent
from api.services.classification import classify_category

DEFAULT_FEEDS = [
    "https://feeds.reuters.com/reuters/businessNews",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://feeds.marketwatch.com/marketwatch/topstories/",
]



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



def fetch_feed_events(feed_url: str, timeout_seconds: float = 10.0) -> list[NormalizedNewsEvent]:
    with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
        response = client.get(feed_url)
        response.raise_for_status()

    root = ET.fromstring(response.text)
    items = root.findall("./channel/item")

    events: list[NormalizedNewsEvent] = []
    for item in items[:50]:
        parsed = _parse_item(item, feed_url)
        if parsed is not None:
            events.append(parsed)
    return events



def collect_events(feed_urls: list[str] | None = None) -> list[NormalizedNewsEvent]:
    urls = feed_urls or DEFAULT_FEEDS
    results: list[NormalizedNewsEvent] = []
    for url in urls:
        try:
            results.extend(fetch_feed_events(url))
        except Exception:
            # Continue on source-level failures to keep ingestion resilient.
            continue
    return results
