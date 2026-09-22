import sys
from pathlib import Path

from loguru import logger

from app.core.config import get_settings

CONSOLE_LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

FILE_LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}"
)


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
        format=CONSOLE_LOG_FORMAT,
    )

    if not settings.logging_file_enabled:
        return

    log_path = Path(settings.logging_file_path)
    log_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    logger.add(
        log_path,
        level=log_level,
        rotation=settings.logging_rotation,
        retention=settings.logging_retention,
        compression="gz",
        enqueue=True,
        backtrace=False,
        diagnose=False,
        encoding="utf-8",
        format=FILE_LOG_FORMAT,
    )
