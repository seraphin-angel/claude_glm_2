"""Structured logging configuration using structlog.

This module provides JSON-formatted structured logging with:
- Request ID correlation
- Sensitive data masking
- Configurable log levels
- ISO 8601 timestamps
"""

import logging
import os
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

import structlog
from structlog.types import Processor

# Context variable for request ID
_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)

# Keys that should be masked in logs
SENSITIVE_KEYS = frozenset([
    "password",
    "passwd",
    "secret",
    "api_key",
    "apikey",
    "token",
    "authorization",
    "credential",
    "private_key",
    "access_token",
    "refresh_token",
])


def mask_sensitive_data(
    key: str,
    value: Any,
    sensitive_keys: frozenset[str] = SENSITIVE_KEYS,
) -> Any:
    """Mask sensitive data in log output.

    Args:
        key: The key name of the value
        value: The value to potentially mask
        sensitive_keys: Set of keys that should be masked

    Returns:
        Masked value if key is sensitive, otherwise original value
    """
    if key.lower() in sensitive_keys:
        if isinstance(value, str) and len(value) > 4:
            return f"{value[:2]}***{value[-2:]}"
        return "***MASKED***"
    return value


def sensitive_data_masker(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor to mask sensitive data.

    Args:
        logger: The wrapped logger object
        method_name: The name of the wrapped method (e.g. 'info', 'debug')
        event_dict: The event dictionary to process

    Returns:
        The event dictionary with sensitive values masked
    """
    return {
        key: mask_sensitive_data(key, value)
        for key, value in event_dict.items()
    }


def add_request_id(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor to add request ID from context.

    Args:
        logger: The wrapped logger object
        method_name: The name of the wrapped method
        event_dict: The event dictionary to process

    Returns:
        The event dictionary with request_id added if available
    """
    request_id = get_request_id()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def timestamp_in_iso8601(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor to add ISO 8601 timestamp.

    Args:
        logger: The wrapped logger object
        method_name: The name of the wrapped method
        event_dict: The event dictionary to process

    Returns:
        The event dictionary with timestamp added
    """
    event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
    return event_dict


def get_log_level() -> int:
    """Get the log level from environment variable.

    Returns:
        The logging level (default: INFO)
    """
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    return getattr(logging, level_name, logging.INFO)


def configure_logging(json_output: bool = True) -> None:
    """Configure structured logging.

    Args:
        json_output: If True, output JSON format; if False, use console format
    """
    log_level = get_log_level()

    # Configure standard library logging
    # Force reconfiguration by setting root logger level directly
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers and add our own
    if root_logger.handlers:
        root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.setLevel(log_level)
    root_logger.addHandler(handler)

    # Common processors for all loggers
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamp_in_iso8601,
        add_request_id,
        sensitive_data_masker,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_output:
        # JSON output configuration
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Human-readable console output
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a configured structlog logger.

    Args:
        name: The logger name (typically __name__)

    Returns:
        A configured structlog logger instance
    """
    return structlog.get_logger(name)


def set_request_id(request_id: str) -> None:
    """Set the request ID in the current context.

    Args:
        request_id: The request ID to set
    """
    _request_id_ctx.set(request_id)


def get_request_id() -> str | None:
    """Get the request ID from the current context.

    Returns:
        The current request ID, or None if not set
    """
    return _request_id_ctx.get()


def clear_request_id() -> None:
    """Clear the request ID from the current context."""
    _request_id_ctx.set(None)
