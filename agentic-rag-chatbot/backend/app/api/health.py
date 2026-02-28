"""Health check endpoints for the API."""

import time
from datetime import UTC, datetime
from typing import Optional

import psutil
from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.llm_factory import get_llm
from app.config.settings import get_settings
from app.rag.vector_store import VectorStore

router = APIRouter(tags=["health"])


# Pydantic models for health response
class ChromaDBCheck(BaseModel):
    """ChromaDB health check result."""

    status: str
    document_count: int = 0
    error: Optional[str] = None


class OpenAICheck(BaseModel):
    """OpenAI API health check result."""

    status: str
    latency_ms: Optional[int] = None
    error: Optional[str] = None


class MemoryCheck(BaseModel):
    """Memory usage metrics."""

    used_mb: int
    available_mb: int
    percent: float


class SessionsCheck(BaseModel):
    """Active sessions count."""

    active: int


class PersistenceCheck(BaseModel):
    """Persistence layer health check result."""

    status: str  # "ok" or "degraded"
    healthy: bool
    message: str


class HealthChecks(BaseModel):
    """All health check results."""

    chromadb: ChromaDBCheck
    openai: OpenAICheck
    memory: MemoryCheck
    sessions: SessionsCheck
    persistence: PersistenceCheck


class HealthResponse(BaseModel):
    """Detailed health response."""

    status: str  # "healthy", "degraded", or "unhealthy"
    timestamp: datetime
    checks: HealthChecks


def check_chromadb() -> ChromaDBCheck:
    """Check ChromaDB connection and get document count."""
    try:
        store = VectorStore.get_instance()
        count = store.count
        return ChromaDBCheck(status="ok", document_count=count)
    except Exception as e:
        return ChromaDBCheck(status="error", document_count=0, error=str(e))


async def check_openai() -> OpenAICheck:
    """Check OpenAI API reachability with a lightweight call."""
    try:
        llm = get_llm()
        start_time = time.time()
        # Use a minimal prompt to check API reachability
        await llm.ainvoke("ping")
        latency_ms = int((time.time() - start_time) * 1000)
        return OpenAICheck(status="ok", latency_ms=latency_ms)
    except Exception as e:
        return OpenAICheck(status="error", error=str(e))


def get_system_metrics() -> MemoryCheck:
    """Get system memory metrics using psutil."""
    memory = psutil.virtual_memory()
    return MemoryCheck(
        used_mb=int(memory.used / (1024 * 1024)),
        available_mb=int(memory.available / (1024 * 1024)),
        percent=memory.percent,
    )


async def get_active_sessions() -> SessionsCheck:
    """Get count of active sessions from PostgresSaver checkpoint table.

    Returns the number of unique thread_ids (sessions) that have checkpoints.
    Falls back to 0 if database is not available.
    """
    try:
        from app.agents.agent import get_checkpointer

        checkpointer = get_checkpointer()

        # PostgresSaver の場合、checkpoint テーブルからセッション数を取得
        if hasattr(checkpointer, "conn"):
            # AsyncPostgresSaver の場合
            import asyncpg

            conn = checkpointer.conn
            if isinstance(conn, asyncpg.Connection):
                result = await conn.fetchval(
                    "SELECT COUNT(DISTINCT thread_id) FROM checkpoints"
                )
                return SessionsCheck(active=result or 0)

        # MemorySaver の場合や、その他の場合は0を返す
        return SessionsCheck(active=0)

    except Exception:
        # データベース接続エラーなどの場合は0を返す（graceful degradation）
        return SessionsCheck(active=0)


def determine_health_status(checks: HealthChecks) -> str:
    """Determine overall health status based on individual checks."""
    statuses = [
        checks.chromadb.status,
        checks.openai.status,
        checks.persistence.status,
    ]

    if all(s == "ok" for s in statuses):
        return "healthy"
    elif any(s == "ok" for s in statuses):
        return "degraded"
    else:
        return "unhealthy"


def check_persistence() -> PersistenceCheck:
    """Check if persistence layer is healthy.

    Returns:
        PersistenceCheck with status, healthy flag, and message.
    """
    from app.agents.agent import is_persistence_healthy

    healthy = is_persistence_healthy()
    if healthy:
        return PersistenceCheck(
            status="ok",
            healthy=True,
            message="Persistence layer is functioning normally",
        )
    else:
        return PersistenceCheck(
            status="degraded",
            healthy=False,
            message="PostgresSaver fallback to MemorySaver - session history will not persist",
        )


@router.get("/api/health")
async def health():
    """Basic health check endpoint."""
    settings = get_settings()
    return {"status": "ok", "version": settings.app_version}


@router.get("/api/health/detailed", response_model=HealthResponse)
async def detailed_health():
    """Detailed health check with all system components."""
    # Run checks
    chromadb_check = check_chromadb()
    openai_check = await check_openai()
    memory_check = get_system_metrics()
    sessions_check = await get_active_sessions()
    persistence_check = check_persistence()

    checks = HealthChecks(
        chromadb=chromadb_check,
        openai=openai_check,
        memory=memory_check,
        sessions=sessions_check,
        persistence=persistence_check,
    )

    status = determine_health_status(checks)

    return HealthResponse(
        status=status,
        timestamp=datetime.now(UTC),
        checks=checks,
    )
