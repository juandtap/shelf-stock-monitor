from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.scheduler.monitoring_job import run_monitoring_cycle
from app.scheduler.monitoring_scheduler import MonitoringScheduler
from app.telegram.client import TelegramBotClient
from app.telegram.polling_service import TelegramPollingService

settings = get_settings()

configure_logging()


def create_telegram_polling_service() -> TelegramPollingService | None:
    polling_enabled = settings.telegram_polling_enabled and settings.app_env == "development"

    if not polling_enabled:
        return None

    if settings.telegram_bot_token is None:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is required when TELEGRAM_POLLING_ENABLED=true.",
        )

    if settings.telegram_chat_id is None:
        raise RuntimeError(
            "TELEGRAM_CHAT_ID is required when TELEGRAM_POLLING_ENABLED=true.",
        )

    client = TelegramBotClient(
        bot_token=settings.telegram_bot_token.get_secret_value(),
        request_timeout_seconds=(settings.telegram_request_timeout_seconds),
        polling_timeout_seconds=(settings.telegram_polling_timeout_seconds),
    )

    return TelegramPollingService(
        client=client,
        session_factory=SessionLocal,
        allowed_chat_id=settings.telegram_chat_id,
    )


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncIterator[None]:
    logger.info(
        "Application starting | environment={}",
        settings.app_env,
    )

    scheduler_enabled = settings.monitoring_enabled and settings.app_env != "testing"

    monitoring_scheduler = MonitoringScheduler(
        enabled=scheduler_enabled,
        interval_minutes=settings.monitoring_interval_minutes,
        job=run_monitoring_cycle,
    )

    monitoring_scheduler.start()

    telegram_polling_service = create_telegram_polling_service()

    if telegram_polling_service is not None:
        telegram_polling_service.start()

    app.state.monitoring_scheduler = monitoring_scheduler
    app.state.telegram_polling_service = telegram_polling_service

    try:
        yield
    finally:
        if telegram_polling_service is not None:
            await telegram_polling_service.shutdown()

        monitoring_scheduler.shutdown()

        logger.info(
            "Application stopped",
        )


app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    lifespan=lifespan,
)

app.include_router(api_router)


@app.get(
    "/health",
    tags=["Health"],
)
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "environment": settings.app_env,
    }
