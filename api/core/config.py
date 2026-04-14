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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
