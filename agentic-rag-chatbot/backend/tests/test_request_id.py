"""Tests for request ID middleware and correlation."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.core.logging import get_request_id, set_request_id, clear_request_id


class TestRequestIdMiddleware:
    """Test request ID middleware functionality."""

    def test_request_id_generated_when_not_provided(self):
        """Test that a request ID is generated when not provided in headers."""
        client = TestClient(app)

        response = client.get("/api/health")

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"] != ""

    def test_request_id_preserved_from_header(self):
        """Test that request ID is preserved from X-Request-ID header."""
        client = TestClient(app)
        test_request_id = "test-request-abc-123"

        response = client.get("/api/health", headers={"X-Request-ID": test_request_id})

        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == test_request_id

    def test_request_id_format_is_uuid4(self):
        """Test that generated request ID is in UUID4 format."""
        client = TestClient(app)

        response = client.get("/api/health")
        request_id = response.headers["X-Request-ID"]

        # UUID4 format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
        import re
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        assert uuid_pattern.match(request_id) is not None

    def test_different_requests_have_different_ids(self):
        """Test that different requests get different request IDs."""
        client = TestClient(app)

        response1 = client.get("/api/health")
        response2 = client.get("/api/health")

        assert response1.headers["X-Request-ID"] != response2.headers["X-Request-ID"]


class TestRequestIdContext:
    """Test request ID context management in middleware."""

    def test_request_id_cleared_after_request(self):
        """Test that request ID is cleared after request completes."""
        client = TestClient(app)

        # Make a request
        client.get("/api/health")

        # Request ID should be cleared after the request
        assert get_request_id() is None

    def test_request_id_matches_response_header(self):
        """Test that request ID in response matches the one set during request."""
        client = TestClient(app)
        test_request_id = "test-req-match-123"

        response = client.get("/api/health", headers={"X-Request-ID": test_request_id})

        # Response header should have the same request ID
        assert response.headers["X-Request-ID"] == test_request_id
