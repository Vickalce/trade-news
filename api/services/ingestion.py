from api.providers.news import get_news_provider
from api.schemas import NormalizedNewsEvent



def collect_events(feed_urls: list[str] | None = None) -> list[NormalizedNewsEvent]:
    # feed_urls is kept for compatibility; provider config now drives source selection.
    _ = feed_urls
    provider = get_news_provider()
    return provider.collect_events()
