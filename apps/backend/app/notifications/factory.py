from app.core.config import Settings
from app.notifications.logging_provider import LoggingNotificationProvider
from app.notifications.provider import NotificationProvider
from app.notifications.telegram_provider import TelegramNotificationProvider


class InvalidNotificationConfigurationError(Exception):
    pass


def create_notification_provider(
    settings: Settings,
) -> NotificationProvider:
    if settings.notification_provider == "logging":
        return LoggingNotificationProvider()

    if settings.notification_provider == "telegram":
        if settings.telegram_bot_token is None:
            raise InvalidNotificationConfigurationError(
                "TELEGRAM_BOT_TOKEN is required when NOTIFICATION_PROVIDER=telegram."
            )

        if settings.telegram_chat_id is None:
            raise InvalidNotificationConfigurationError(
                "TELEGRAM_CHAT_ID is required when NOTIFICATION_PROVIDER=telegram."
            )

        return TelegramNotificationProvider(
            bot_token=settings.telegram_bot_token.get_secret_value(),
            chat_id=settings.telegram_chat_id,
            timeout_seconds=settings.telegram_request_timeout_seconds,
        )

    raise InvalidNotificationConfigurationError(
        f"Unsupported notification provider: {settings.notification_provider}"
    )
