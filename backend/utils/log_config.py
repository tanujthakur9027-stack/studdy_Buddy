"""
utils/log_config.py — Structured JSON logging setup for StudyBuddy.

Produces one JSON line per log record with fields:
  timestamp, level, logger, message, [exc_info], [request_id], [latency_ms]

Usage:
    from utils.log_config import setup_logging
    setup_logging()          # call once at startup (main.py)

Individual loggers then just use the standard library:
    import logging
    log = logging.getLogger(__name__)
    log.info("LLM call", extra={"model": "gpt-4o-mini", "tokens": 320, "latency_ms": 812})
"""
from __future__ import annotations

import logging
import sys
from typing import Any

from pythonjsonlogger import jsonlogger


class _StudyBuddyFormatter(jsonlogger.JsonFormatter):
    """Adds a 'service' field and renames 'levelname' → 'level'."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["service"] = "studybuddy-api"
        # Normalise field names
        if "levelname" in log_record:
            log_record["level"] = log_record.pop("levelname").lower()
        if "asctime" in log_record:
            log_record["timestamp"] = log_record.pop("asctime")


def setup_logging(level: str = "INFO") -> None:
    """
    Replace the root logger's handler with a JSON-streaming handler.
    Safe to call multiple times (idempotent — checks for existing handler).
    """
    root = logging.getLogger()

    # Avoid double-adding if already configured
    if any(isinstance(h, logging.StreamHandler) and
           isinstance(getattr(h, "formatter", None), jsonlogger.JsonFormatter)
           for h in root.handlers):
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_StudyBuddyFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    ))

    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Quiet down noisy libraries
    for noisy in ("uvicorn.access", "httpx", "chromadb", "faiss"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
