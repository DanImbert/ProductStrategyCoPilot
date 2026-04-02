"""Structured logging configuration for local and deployed environments."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .core.config import Settings


class JsonLogFormatter(logging.Formatter):
    """Small JSON formatter for consistent logs in containers and PaaS deployments."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "event"):
            payload["event"] = getattr(record, "event")
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(settings: Settings) -> logging.Logger:
    """Configure root logging once and return the root logger."""

    root_logger = logging.getLogger()
    if getattr(root_logger, "_product_strategy_copilot_configured", False):
        return root_logger

    root_logger.handlers.clear()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    formatter = JsonLogFormatter()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if settings.enable_file_logging:
        log_path = Path(settings.log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    root_logger._product_strategy_copilot_configured = True  # type: ignore[attr-defined]
    return root_logger
