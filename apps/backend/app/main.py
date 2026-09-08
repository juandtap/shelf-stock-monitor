from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.scheduler.monitoring_job import run_monitoring_cycle
from app.scheduler.monitoring_scheduler import MonitoringScheduler

settings = get_settings()

configure_logging()


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

    app.state.monitoring_scheduler = monitoring_scheduler

    try:
        yield
    finally:
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
