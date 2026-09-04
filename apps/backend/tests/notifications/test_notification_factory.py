from typing import Literal

from pydantic import SecretStr

from app.core.config import Settings
from app.notifications.factory import (
    InvalidNotificationConfigurationError,
    create_notification_provider,
)
from app.notifications.logging_provider import LoggingNotificationProvider
from app.notifications.telegram_provider import TelegramNotificationProvider

NotificationProviderName = Literal["logging", "telegram"]


def create_settings(
    *,
    notification_provider: NotificationProviderName = "logging",
    telegram_bot_token: SecretStr | None = None,
    telegram_chat_id: str | None = None,
) -> Settings:
    return Settings(
        database_host="localhost",
        database_port=5432,
        database_name="shelf_stock",
        database_test_name="shelf_stock_test",
        database_user="shelf_stock",
        database_password=SecretStr("test"),
        notification_provider=notification_provider,
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=telegram_chat_id,
    )


def test_creates_logging_provider() -> None:
    settings = create_settings()

    provider = create_notification_provider(settings)

    assert isinstance(provider, LoggingNotificationProvider)


def test_creates_telegram_provider() -> None:
    settings = create_settings(
        notification_provider="telegram",
        telegram_bot_token=SecretStr("test-token"),
        telegram_chat_id="123456789",
    )

    provider = create_notification_provider(settings)

    assert isinstance(provider, TelegramNotificationProvider)


def test_telegram_provider_requires_bot_token() -> None:
    settings = create_settings(
        notification_provider="telegram",
        telegram_chat_id="123456789",
    )

    try:
        create_notification_provider(settings)
    except InvalidNotificationConfigurationError as exc:
        assert "TELEGRAM_BOT_TOKEN" in str(exc)
    else:
        raise AssertionError("Expected InvalidNotificationConfigurationError.")


def test_telegram_provider_requires_chat_id() -> None:
    settings = create_settings(
        notification_provider="telegram",
        telegram_bot_token=SecretStr("test-token"),
    )

    try:
        create_notification_provider(settings)
    except InvalidNotificationConfigurationError as exc:
        assert "TELEGRAM_CHAT_ID" in str(exc)
    else:
        raise AssertionError("Expected InvalidNotificationConfigurationError.")
