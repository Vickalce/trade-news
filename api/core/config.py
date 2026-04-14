from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Trade News"
    app_env: str = "local"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://trade_news:trade_news@localhost:5432/trade_news"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
