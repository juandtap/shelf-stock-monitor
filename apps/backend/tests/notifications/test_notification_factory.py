from typing import Literal

import pytest
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
        mlflow_tracking_uri="sqlite:///test-mlflow.db",
        mlflow_experiment_name="test-benchmarks",
        notification_provider=notification_provider,
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=telegram_chat_id,
    )


def test_create_logging_notification_provider() -> None:
    settings = create_settings(
        notification_provider="logging",
    )

    provider = create_notification_provider(settings)

    assert isinstance(
        provider,
        LoggingNotificationProvider,
    )


def test_create_telegram_notification_provider() -> None:
    settings = create_settings(
        notification_provider="telegram",
        telegram_bot_token=SecretStr("test-token"),
        telegram_chat_id="test-chat",
    )

    provider = create_notification_provider(settings)

    assert isinstance(
        provider,
        TelegramNotificationProvider,
    )


def test_create_telegram_notification_provider_requires_token() -> None:
    settings = create_settings(
        notification_provider="telegram",
        telegram_chat_id="test-chat",
    )

    with pytest.raises(
        InvalidNotificationConfigurationError,
        match=("TELEGRAM_BOT_TOKEN is required when NOTIFICATION_PROVIDER=telegram."),
    ):
        create_notification_provider(settings)


def test_create_telegram_notification_provider_requires_chat_id() -> None:
    settings = create_settings(
        notification_provider="telegram",
        telegram_bot_token=SecretStr("test-token"),
    )

    with pytest.raises(
        InvalidNotificationConfigurationError,
        match=("TELEGRAM_CHAT_ID is required when NOTIFICATION_PROVIDER=telegram."),
    ):
        create_notification_provider(settings)
