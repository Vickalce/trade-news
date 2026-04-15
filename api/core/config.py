from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Trade News"
    app_env: str = "local"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://trade_news:trade_news@localhost:5432/trade_news"
    alert_output_dir: str = "alerts/outbox"
    pipeline_default_limit: int = 20
    min_confidence_threshold: float = 55.0
    symbol_cooldown_minutes: int = 30
    max_alerts_per_day: int = 100
    kill_switch_enabled: bool = False
    news_provider: str = "rss"
    market_data_provider: str = "yahoo"
    news_timeout_seconds: float = 10.0
    max_feed_items_per_source: int = 50
    enable_live_market_data: bool = True
    market_data_timeout_seconds: float = 6.0
    alert_channels_csv: str = "email"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_to_email: str = ""
    discord_webhook_url: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    api_key: str = ""
    rate_limit_window_seconds: int = 60
    rate_limit_max_requests: int = 30
    broker_provider: str = "paper"
    broker_dry_run: bool = True
    broker_kill_switch_enabled: bool = True
    trade_confirm_token: str = "CONFIRM"
    order_max_notional_usd: float = 5000.0
    schwab_base_url: str = "https://api.schwabapi.com/trader/v1"
    schwab_access_token: str = ""
    schwab_client_id: str = ""
    schwab_client_secret: str = ""
    schwab_redirect_uri: str = ""
    schwab_oauth_authorize_url: str = "https://api.schwabapi.com/v1/oauth/authorize"
    schwab_oauth_token_url: str = "https://api.schwabapi.com/v1/oauth/token"
    schwab_oauth_scope: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets/v2"
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    finnhub_base_url: str = "https://finnhub.io/api/v1"
    finnhub_api_key: str = ""
    finnhub_news_category: str = "general"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
