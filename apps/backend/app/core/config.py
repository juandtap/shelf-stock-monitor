from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Shelf Stock Monitor API"
    app_env: Literal["development", "testing", "production"] = "development"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "shelf_stock"
    database_user: str = "shelf_stock"
    database_password: SecretStr

    monitoring_enabled: bool = False
    monitoring_interval_minutes: int = Field(default=30, ge=1)
    monitoring_image_path: str | None = None

    notification_provider: Literal["logging", "telegram"] = "logging"

    telegram_bot_token: SecretStr | None = None
    telegram_chat_id: str | None = None
    telegram_request_timeout_seconds: float = Field(
        default=10.0,
        gt=0,
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        password = self.database_password.get_secret_value()

        return (
            f"postgresql+psycopg://{self.database_user}:{password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
