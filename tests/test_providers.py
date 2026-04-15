from api.core.config import settings
from api.providers.execution import AlpacaBrokerAdapter, PaperBrokerAdapter, SchwabBrokerAdapter, get_broker_adapter
from api.providers.market import (
    DeterministicFallbackMarketProvider,
    FinnhubMarketDataProvider,
    YahooMarketDataProvider,
    get_market_data_provider,
)
from api.providers.news import DemoNewsProvider, FinnhubNewsProvider, RssNewsProvider, get_news_provider
from api.providers.registry import (
    EXECUTION_PROVIDER_REGISTRY,
    MARKET_DATA_PROVIDER_REGISTRY,
    NEWS_PROVIDER_REGISTRY,
    serialize_provider_definition,
)


def test_provider_registries_expose_expected_defaults():
    news_keys = [definition.key for definition in NEWS_PROVIDER_REGISTRY.list_definitions()]
    market_keys = [definition.key for definition in MARKET_DATA_PROVIDER_REGISTRY.list_definitions()]
    execution_keys = [definition.key for definition in EXECUTION_PROVIDER_REGISTRY.list_definitions()]

    assert news_keys == ["demo", "finnhub", "rss"]
    assert market_keys == ["fallback", "finnhub", "yahoo"]
    assert execution_keys == ["alpaca", "paper", "schwab"]


def test_provider_factories_resolve_selected_adapters(monkeypatch):
    monkeypatch.setattr(settings, "news_provider", "demo")
    monkeypatch.setattr(settings, "market_data_provider", "fallback")
    monkeypatch.setattr(settings, "broker_provider", "paper")

    assert isinstance(get_news_provider(), DemoNewsProvider)
    assert isinstance(get_market_data_provider(), DeterministicFallbackMarketProvider)
    assert isinstance(get_broker_adapter(), PaperBrokerAdapter)

    monkeypatch.setattr(settings, "news_provider", "rss")
    monkeypatch.setattr(settings, "market_data_provider", "yahoo")
    monkeypatch.setattr(settings, "broker_provider", "schwab")

    assert isinstance(get_news_provider(), RssNewsProvider)
    assert isinstance(get_market_data_provider(), YahooMarketDataProvider)
    assert isinstance(get_broker_adapter(), SchwabBrokerAdapter)

    monkeypatch.setattr(settings, "news_provider", "finnhub")
    monkeypatch.setattr(settings, "market_data_provider", "finnhub")
    monkeypatch.setattr(settings, "broker_provider", "alpaca")

    assert isinstance(get_news_provider(), FinnhubNewsProvider)
    assert isinstance(get_market_data_provider(), FinnhubMarketDataProvider)
    assert isinstance(get_broker_adapter(), AlpacaBrokerAdapter)


def test_provider_metadata_reports_configuration_status(monkeypatch):
    definition = EXECUTION_PROVIDER_REGISTRY.get_definition("schwab")

    monkeypatch.setattr(settings, "schwab_client_id", "")
    monkeypatch.setattr(settings, "schwab_client_secret", "")
    monkeypatch.setattr(settings, "schwab_redirect_uri", "")
    unconfigured = serialize_provider_definition(definition, selected_key="schwab")
    assert unconfigured["selected"] is True
    assert unconfigured["configured"] is False
    assert unconfigured["capabilities"]["auth_type"] == "oauth2"

    monkeypatch.setattr(settings, "schwab_client_id", "client")
    monkeypatch.setattr(settings, "schwab_client_secret", "secret")
    monkeypatch.setattr(settings, "schwab_redirect_uri", "https://example.com/callback")
    configured = serialize_provider_definition(definition, selected_key="schwab")
    assert configured["configured"] is True


def test_api_key_provider_metadata_reports_configuration_status(monkeypatch):
    finnhub_def = NEWS_PROVIDER_REGISTRY.get_definition("finnhub")
    alpaca_def = EXECUTION_PROVIDER_REGISTRY.get_definition("alpaca")

    monkeypatch.setattr(settings, "finnhub_api_key", "")
    unconfigured_news = serialize_provider_definition(finnhub_def, selected_key="finnhub")
    assert unconfigured_news["configured"] is False
    assert unconfigured_news["capabilities"]["auth_type"] == "api_key"

    monkeypatch.setattr(settings, "finnhub_api_key", "token")
    configured_news = serialize_provider_definition(finnhub_def, selected_key="finnhub")
    assert configured_news["configured"] is True

    monkeypatch.setattr(settings, "alpaca_api_key", "")
    monkeypatch.setattr(settings, "alpaca_secret_key", "")
    unconfigured_exec = serialize_provider_definition(alpaca_def, selected_key="alpaca")
    assert unconfigured_exec["configured"] is False

    monkeypatch.setattr(settings, "alpaca_api_key", "key")
    monkeypatch.setattr(settings, "alpaca_secret_key", "secret")
    configured_exec = serialize_provider_definition(alpaca_def, selected_key="alpaca")
    assert configured_exec["configured"] is True