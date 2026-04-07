"""
Shared logger using loguru – centralised logging configuration for the entire app.
"""

import sys
from pathlib import Path

from loguru import logger

from config.settings import settings


def configure_logger() -> None:
    """
    Configures the global loguru logger with a modern, premium layout.
    """
    # 1. Clear default handlers
    logger.remove()

    # 2. Add console handler with premium formatting
    # Note: <level> tags use colors assigned to log levels (INFO=white, DEBUG=blue, etc.)
    fmt = (
        "<white>{time:YYYY-MM-DD HH:mm:ss.SSS}</white> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
        "- <level>{message}</level>"
    )

    logger.add(
        sys.stdout,
        level=settings.log_level,
        format=fmt,
        colorize=True,
        enqueue=True, # Thread-safe
    )

    # 3. Add file handler for persistence
    log_file = Path("logs/app.log")
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        str(log_file),
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        enqueue=True, # Thread-safe & non-blocking
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    logger.info("Logger configured – level: {}, environment: {}", 
                settings.log_level, getattr(settings, "env", "production"))


# Auto-configure on import
configure_logger()

__all__ = ["logger"]
