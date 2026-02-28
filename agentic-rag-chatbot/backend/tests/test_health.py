"""Tests for detailed health check endpoint."""

import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.api.health import (
    ChromaDBCheck,
    HealthResponse,
    MemoryCheck,
    OpenAICheck,
    SessionsCheck,
    check_chromadb,
    check_openai,
    get_system_metrics,
    router,
)
from app.main import app


class TestPersistenceHealthCheck:
    """persistence ヘルスチェックのテスト（TDD: Issue #1）"""

    @pytest.mark.asyncio
    async def test_detailed_health_includes_persistence_check(self):
        """detailed health エンドポイントに persistence チェックが含まれることをテスト"""
        with (
            patch("app.api.health.VectorStore") as mock_store,
            patch("app.api.health.get_llm") as mock_get_llm,
            patch("app.api.health.psutil") as mock_psutil,
            patch("app.agents.agent.is_persistence_healthy", return_value=True),
        ):
            # Mock ChromaDB
            mock_instance = MagicMock()
            mock_instance.count = 150
            mock_store.get_instance.return_value = mock_instance

            # Mock OpenAI
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="pong"))
            mock_get_llm.return_value = mock_llm

            # Mock psutil
            mock_memory = MagicMock()
            mock_memory.used = 256 * 1024 * 1024
            mock_memory.available = 1024 * 1024 * 1024
            mock_memory.percent = 25.0
            mock_psutil.virtual_memory.return_value = mock_memory

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/health/detailed")

                assert response.status_code == 200
                data = response.json()
                assert "persistence" in data["checks"]

    @pytest.mark.asyncio
    async def test_persistence_check_returns_healthy_when_true(self):
        """persistence が正常な場合 ok ステータスを返すことをテスト"""
        with (
            patch("app.api.health.VectorStore") as mock_store,
            patch("app.api.health.get_llm") as mock_get_llm,
            patch("app.api.health.psutil") as mock_psutil,
            patch("app.agents.agent.is_persistence_healthy", return_value=True),
        ):
            mock_instance = MagicMock()
            mock_instance.count = 150
            mock_store.get_instance.return_value = mock_instance

            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="pong"))
            mock_get_llm.return_value = mock_llm

            mock_memory = MagicMock()
            mock_memory.used = 256 * 1024 * 1024
            mock_memory.available = 1024 * 1024 * 1024
            mock_memory.percent = 25.0
            mock_psutil.virtual_memory.return_value = mock_memory

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/health/detailed")

                data = response.json()
                assert data["checks"]["persistence"]["status"] == "ok"
                assert data["checks"]["persistence"]["healthy"] is True

    @pytest.mark.asyncio
    async def test_persistence_check_returns_degraded_when_false(self):
        """persistence がフォールバック状態の場合 degraded ステータスになることをテスト"""
        with (
            patch("app.api.health.VectorStore") as mock_store,
            patch("app.api.health.get_llm") as mock_get_llm,
            patch("app.api.health.psutil") as mock_psutil,
            patch("app.agents.agent.is_persistence_healthy", return_value=False),
        ):
            mock_instance = MagicMock()
            mock_instance.count = 150
            mock_store.get_instance.return_value = mock_instance

            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="pong"))
            mock_get_llm.return_value = mock_llm

            mock_memory = MagicMock()
            mock_memory.used = 256 * 1024 * 1024
            mock_memory.available = 1024 * 1024 * 1024
            mock_memory.percent = 25.0
            mock_psutil.virtual_memory.return_value = mock_memory

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/health/detailed")

                data = response.json()
                assert data["checks"]["persistence"]["status"] == "degraded"
                assert data["checks"]["persistence"]["healthy"] is False
                assert "fallback" in data["checks"]["persistence"]["message"].lower()

    @pytest.mark.asyncio
    async def test_overall_status_degraded_when_persistence_fails(self):
        """persistence が失敗している場合全体のステータスが degraded になることをテスト"""
        with (
            patch("app.api.health.VectorStore") as mock_store,
            patch("app.api.health.get_llm") as mock_get_llm,
            patch("app.api.health.psutil") as mock_psutil,
            patch("app.agents.agent.is_persistence_healthy", return_value=False),
        ):
            mock_instance = MagicMock()
            mock_instance.count = 150
            mock_store.get_instance.return_value = mock_instance

            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="pong"))
            mock_get_llm.return_value = mock_llm

            mock_memory = MagicMock()
            mock_memory.used = 256 * 1024 * 1024
            mock_memory.available = 1024 * 1024 * 1024
            mock_memory.percent = 25.0
            mock_psutil.virtual_memory.return_value = mock_memory

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/health/detailed")

                data = response.json()
                # persistence が degraded なので全体も degraded
                assert data["status"] == "degraded"


class TestHealthModels:
    """Test Pydantic models for health response."""

    def test_chromadb_check_model(self):
        """Test ChromaDBCheck model creation."""
        check = ChromaDBCheck(status="ok", document_count=150)
        assert check.status == "ok"
        assert check.document_count == 150

    def test_chromadb_check_with_error(self):
        """Test ChromaDBCheck model with error status."""
        check = ChromaDBCheck(status="error", document_count=0, error="Connection failed")
        assert check.status == "error"
        assert check.error == "Connection failed"

    def test_openai_check_model(self):
        """Test OpenAICheck model creation."""
        check = OpenAICheck(status="ok", latency_ms=120)
        assert check.status == "ok"
        assert check.latency_ms == 120

    def test_openai_check_with_error(self):
        """Test OpenAICheck model with error status."""
        check = OpenAICheck(status="error", error="API key invalid")
        assert check.status == "error"
        assert check.error == "API key invalid"

    def test_memory_check_model(self):
        """Test MemoryCheck model creation."""
        check = MemoryCheck(used_mb=256, available_mb=1024, percent=25.0)
        assert check.used_mb == 256
        assert check.available_mb == 1024
        assert check.percent == 25.0

    def test_sessions_check_model(self):
        """Test SessionsCheck model creation."""
        check = SessionsCheck(active=5)
        assert check.active == 5

    def test_health_response_model(self):
        """Test HealthResponse model creation."""
        from app.api.health import HealthChecks, PersistenceCheck

        checks = HealthChecks(
            chromadb=ChromaDBCheck(status="ok", document_count=150),
            openai=OpenAICheck(status="ok", latency_ms=120),
            memory=MemoryCheck(used_mb=256, available_mb=1024, percent=25.0),
            sessions=SessionsCheck(active=5),
            persistence=PersistenceCheck(status="ok", healthy=True, message="PostgreSQL connected"),
        )
        response = HealthResponse(
            status="healthy",
            timestamp=datetime(2026, 2, 24, 10, 0, 0),
            checks=checks,
        )
        assert response.status == "healthy"
        assert response.checks.chromadb.document_count == 150


class TestCheckFunctions:
    """Test individual check functions."""

    def test_check_chromadb_success(self):
        """Test ChromaDB check when connection is successful."""
        with patch("app.api.health.VectorStore") as mock_store:
            mock_instance = MagicMock()
            mock_instance.count = 150
            mock_store.get_instance.return_value = mock_instance

            result = check_chromadb()

            assert result.status == "ok"
            assert result.document_count == 150
            assert result.error is None

    def test_check_chromadb_failure(self):
        """Test ChromaDB check when connection fails."""
        with patch("app.api.health.VectorStore") as mock_store:
            mock_store.get_instance.side_effect = Exception("Connection refused")

            result = check_chromadb()

            assert result.status == "error"
            assert result.document_count == 0
            assert "Connection refused" in result.error

    @pytest.mark.asyncio
    async def test_check_openai_success(self):
        """Test OpenAI check when API is reachable."""
        with patch("app.api.health.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="pong"))
            mock_get_llm.return_value = mock_llm

            result = await check_openai()

            assert result.status == "ok"
            assert result.latency_ms is not None
            assert result.latency_ms >= 0
            assert result.error is None

    @pytest.mark.asyncio
    async def test_check_openai_failure(self):
        """Test OpenAI check when API is unreachable."""
        with patch("app.api.health.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(side_effect=Exception("API error"))
            mock_get_llm.return_value = mock_llm

            result = await check_openai()

            assert result.status == "error"
            assert result.error == "API error"

    def test_get_system_metrics(self):
        """Test system metrics collection."""
        with patch("app.api.health.psutil") as mock_psutil:
            mock_memory = MagicMock()
            mock_memory.used = 256 * 1024 * 1024  # 256 MB
            mock_memory.available = 1024 * 1024 * 1024  # 1024 MB
            mock_memory.percent = 25.0
            mock_psutil.virtual_memory.return_value = mock_memory

            result = get_system_metrics()

            assert result.used_mb == 256
            assert result.available_mb == 1024
            assert result.percent == 25.0


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_basic_health_endpoint(self):
        """Test basic /api/health endpoint."""
        client = TestClient(app)
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    @pytest.mark.asyncio
    async def test_detailed_health_endpoint(self):
        """Test /api/health/detailed endpoint."""
        with (
            patch("app.api.health.VectorStore") as mock_store,
            patch("app.api.health.get_llm") as mock_get_llm,
            patch("app.api.health.psutil") as mock_psutil,
        ):
            # Mock ChromaDB
            mock_instance = MagicMock()
            mock_instance.count = 150
            mock_store.get_instance.return_value = mock_instance

            # Mock OpenAI
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="pong"))
            mock_get_llm.return_value = mock_llm

            # Mock psutil
            mock_memory = MagicMock()
            mock_memory.used = 256 * 1024 * 1024
            mock_memory.available = 1024 * 1024 * 1024
            mock_memory.percent = 25.0
            mock_psutil.virtual_memory.return_value = mock_memory

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/health/detailed")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] in ["healthy", "degraded", "unhealthy"]
            assert "timestamp" in data
            assert "checks" in data

            # Check ChromaDB
            assert "chromadb" in data["checks"]
            assert data["checks"]["chromadb"]["status"] == "ok"
            assert data["checks"]["chromadb"]["document_count"] == 150

            # Check OpenAI
            assert "openai" in data["checks"]
            assert data["checks"]["openai"]["status"] == "ok"
            assert "latency_ms" in data["checks"]["openai"]

            # Check memory
            assert "memory" in data["checks"]
            assert data["checks"]["memory"]["used_mb"] == 256
            assert data["checks"]["memory"]["available_mb"] == 1024

            # Check sessions
            assert "sessions" in data["checks"]
            assert "active" in data["checks"]["sessions"]

    @pytest.mark.asyncio
    async def test_detailed_health_degraded_status(self):
        """Test that status is 'degraded' when some checks fail."""
        with (
            patch("app.api.health.VectorStore") as mock_store,
            patch("app.api.health.get_llm") as mock_get_llm,
            patch("app.api.health.psutil") as mock_psutil,
        ):
            # Mock ChromaDB failure
            mock_store.get_instance.side_effect = Exception("Connection failed")

            # Mock OpenAI success
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="pong"))
            mock_get_llm.return_value = mock_llm

            # Mock psutil
            mock_memory = MagicMock()
            mock_memory.used = 256 * 1024 * 1024
            mock_memory.available = 1024 * 1024 * 1024
            mock_memory.percent = 25.0
            mock_psutil.virtual_memory.return_value = mock_memory

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/health/detailed")

            assert response.status_code == 200
            data = response.json()

            # Should be degraded since ChromaDB failed
            assert data["status"] in ["degraded", "unhealthy"]
            assert data["checks"]["chromadb"]["status"] == "error"
            assert data["checks"]["openai"]["status"] == "ok"
