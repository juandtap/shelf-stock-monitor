import sys

from loguru import logger

from app.core.config import get_settings


def configure_logging() -> None:
    settings = get_settings()

    logger.remove()

    log_level = "DEBUG" if settings.app_debug else "INFO"

    logger.add(
        sys.stderr,
        level=log_level,
        enqueue=True,
        backtrace=settings.app_debug,
        diagnose=settings.app_debug,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
    )
