"""Centralized structured logging configuration for MantraSetu AgentOS."""

from __future__ import annotations

import json
import logging
import sys
import threading
from typing import Any

_is_configured: bool = False
_logging_lock = threading.Lock()


import contextvars

trace_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)
span_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("span_id", default=None)


class TraceContextFilter(logging.Filter):
    """ContextVar filter to automatically attach trace_id and span_id to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "trace_id"):
            record.trace_id = trace_id_var.get()
        if not hasattr(record, "span_id"):
            record.span_id = span_id_var.get()
        return True


class StructuredJSONFormatter(logging.Formatter):
    """Structured JSON log formatter for production telemetry."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "component": getattr(record, "component", "core"),
        }

        # Contextual metadata
        for field in ("trace_id", "span_id", "request_id", "correlation_id", "session_id", "conversation_id", "execution_time_ms"):
            val = getattr(record, field, None)
            if val is not None:
                log_data[field] = val

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def configure_logging(level: str = "INFO", json_format: bool = False, force: bool = False) -> None:
    """Configure centralized structured application logging thread-safely and idempotently.

    Args:
        level: Logging level string ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL').
        json_format: Boolean flag to enable structured JSON formatting.
        force: Boolean flag to force re-configuration.
    """
    global _is_configured
    with _logging_lock:
        if force:
            _is_configured = False

        if _is_configured:
            return

        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

        # Clear existing handlers to prevent duplicate log records
        root_logger.handlers.clear()

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        handler.addFilter(TraceContextFilter())

        if json_format:
            handler.setFormatter(StructuredJSONFormatter())
        else:
            fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            handler.setFormatter(logging.Formatter(fmt))

        root_logger.addHandler(handler)
        _is_configured = True
