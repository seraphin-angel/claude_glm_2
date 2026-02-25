import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.config.settings import get_settings
from app.core.logging import (
    clear_request_id,
    configure_logging,
    get_logger,
    set_request_id,
)
from app.rate_limit import limiter

# Configure structured logging
configure_logging()

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ドキュメントをロード
    try:
        from app.rag.bm25_store import BM25Store
        from app.rag.document_loader import load_all_documents
        from app.rag.vector_store import VectorStore

        store = VectorStore.get_instance()
        if store.count == 0:
            count = load_all_documents()
            logger.info(f"Loaded {count} document chunks into vector store")
        else:
            logger.info(f"Vector store already has {store.count} documents")

        bm25 = BM25Store.get_instance()
        bm25.build_index_from_vector_store(store)
        logger.info("BM25 index built successfully")
    except Exception as e:
        logger.warning(f"Failed to load documents: {e}")

    yield

    # Shutdown
    logger.info("Shutting down")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware to handle request ID correlation.

    - Reads X-Request-ID from incoming headers
    - Generates a new UUID4 if not provided
    - Sets request ID in context for logging
    - Returns X-Request-ID in response headers
    """

    async def dispatch(self, request: Request, call_next):
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Set in context for logging
        set_request_id(request_id)

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            # Clear context after request
            clear_request_id()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses.

    Logs:
    - Request method, path, and query parameters
    - Response status code
    - Request duration
    - Masks sensitive data in headers and body
    """

    # Headers that should be masked in logs
    SENSITIVE_HEADERS = frozenset([
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "x-auth-token",
    ])

    async def dispatch(self, request: Request, call_next):
        # Record start time
        start_time = time.time()

        # Log request
        await self._log_request(request)

        # Process request
        try:
            response = await call_next(request)

            # Log response
            duration_ms = int((time.time() - start_time) * 1000)
            self._log_response(request, response, duration_ms)

            return response

        except Exception as e:
            # Log error
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "request_error",
                method=request.method,
                path=request.url.path,
                error=str(e),
                duration_ms=duration_ms,
            )
            raise

    async def _log_request(self, request: Request) -> None:
        """Log incoming request details."""
        # Get query params as dict
        query_params = dict(request.query_params) if request.query_params else None

        # Mask sensitive headers
        headers = {}
        for key, value in request.headers.items():
            if key.lower() in self.SENSITIVE_HEADERS:
                headers[key] = self._mask_sensitive(value)
            else:
                headers[key] = value

        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            query_params=query_params,
            client_host=request.client.host if request.client else None,
        )

    def _log_response(
        self,
        request: Request,
        response,
        duration_ms: int,
    ) -> None:
        """Log response details."""
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

    def _mask_sensitive(self, value: str) -> str:
        """Mask sensitive values for logging."""
        if len(value) > 8:
            return f"{value[:4]}...{value[-4:]}"
        return "***MASKED***"


def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "リクエスト回数の上限に達しました。しばらくしてから再度お試しください。"},
    )


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Agentic RAG Chatbot",
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=settings.cors_allowed_methods,
        allow_headers=settings.cors_allowed_headers,
    )
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    from app.api import admin_router, chat_router, faq_router, feedback_router, health_router, knowledge_router

    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(admin_router)
    app.include_router(feedback_router)
    app.include_router(knowledge_router)
    app.include_router(faq_router)

    return app


app = create_app()
