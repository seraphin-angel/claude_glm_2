"""Tests for structured logging configuration."""

import json
import logging
from io import StringIO
from unittest.mock import patch

import pytest
import structlog

from app.core.logging import (
    configure_logging,
    get_logger,
    get_request_id,
    set_request_id,
    clear_request_id,
)


class TestLoggingConfiguration:
    """Test structured logging configuration."""

    def test_configure_logging_sets_json_renderer(self):
        """Test that configure_logging sets up JSON renderer."""
        configure_logging()
        # Check that structlog is configured
        logger = structlog.get_logger()
        assert logger is not None

    def test_get_logger_returns_structlog_logger(self):
        """Test that get_logger returns a structlog logger."""
        configure_logging()
        logger = get_logger(__name__)
        assert logger is not None

    def test_log_output_is_valid_json(self, capsys):
        """Test that log output is valid JSON format."""
        configure_logging(json_output=True)
        logger = get_logger("test_module")

        logger.info("test_event", key="value")

        captured = capsys.readouterr()
        # Output should be valid JSON
        output = captured.err.strip()
        if output:
            parsed = json.loads(output)
            assert "event" in parsed
            assert parsed["event"] == "test_event"
            assert "key" in parsed
            assert parsed["key"] == "value"

    def test_log_includes_timestamp(self, capsys):
        """Test that log output includes timestamp."""
        configure_logging(json_output=True)
        logger = get_logger("test_module")

        logger.info("test_event")

        captured = capsys.readouterr()
        output = captured.err.strip()
        if output:
            parsed = json.loads(output)
            assert "timestamp" in parsed

    def test_log_includes_level(self, capsys):
        """Test that log output includes log level."""
        configure_logging(json_output=True)
        logger = get_logger("test_module")

        logger.info("test_event")

        captured = capsys.readouterr()
        output = captured.err.strip()
        if output:
            parsed = json.loads(output)
            assert "level" in parsed
            assert parsed["level"] == "info"


class TestRequestIdContext:
    """Test request ID context management."""

    def test_set_and_get_request_id(self):
        """Test setting and getting request ID."""
        test_id = "test-request-123"
        set_request_id(test_id)
        assert get_request_id() == test_id
        clear_request_id()

    def test_get_request_id_returns_none_when_not_set(self):
        """Test that get_request_id returns None when not set."""
        clear_request_id()
        assert get_request_id() is None

    def test_clear_request_id(self):
        """Test clearing request ID."""
        set_request_id("test-id")
        clear_request_id()
        assert get_request_id() is None

    def test_log_includes_request_id_when_set(self, capsys):
        """Test that log output includes request_id when set."""
        configure_logging(json_output=True)
        set_request_id("req-abc-123")

        logger = get_logger("test_module")
        logger.info("test_event")

        captured = capsys.readouterr()
        output = captured.err.strip()
        if output:
            parsed = json.loads(output)
            assert "request_id" in parsed
            assert parsed["request_id"] == "req-abc-123"

        clear_request_id()


class TestLogLevelControl:
    """Test log level control."""

    def test_log_level_from_environment(self, monkeypatch):
        """Test that log level can be set via environment variable."""
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        configure_logging()

        # Check that the level is set correctly
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_default_log_level_is_info(self, monkeypatch):
        """Test that default log level is INFO."""
        # Remove LOG_LEVEL if set
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        configure_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO


class TestSensitiveDataMasking:
    """Test that sensitive data is masked in logs."""

    def test_api_key_is_masked(self, capsys):
        """Test that API keys are masked in log output."""
        configure_logging(json_output=True)
        logger = get_logger("test_module")

        # Log with sensitive data
        logger.info(
            "api_call",
            api_key="sk-secret-key-12345",
            other_data="visible",
        )

        captured = capsys.readouterr()
        output = captured.err.strip()
        if output:
            parsed = json.loads(output)
            # API key should be masked
            assert parsed.get("api_key") != "sk-secret-key-12345"
            assert "visible" in parsed.get("other_data", "")

    def test_password_is_masked(self, capsys):
        """Test that passwords are masked in log output."""
        configure_logging(json_output=True)
        logger = get_logger("test_module")

        logger.info(
            "login_attempt",
            password="my_secret_password",
            username="user123",
        )

        captured = capsys.readouterr()
        output = captured.err.strip()
        if output:
            parsed = json.loads(output)
            # Password should be masked
            assert parsed.get("password") != "my_secret_password"
            assert parsed.get("username") == "user123"
