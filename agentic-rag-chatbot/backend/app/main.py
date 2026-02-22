import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.config.settings import get_settings
from app.rate_limit import limiter

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ドキュメントをロード
    try:
        from app.rag.document_loader import load_all_documents
        from app.rag.vector_store import VectorStore

        store = VectorStore.get_instance()
        if store.count == 0:
            count = load_all_documents()
            logger.info(f"Loaded {count} document chunks into vector store")
        else:
            logger.info(f"Vector store already has {store.count} documents")
    except Exception as e:
        logger.warning(f"Failed to load documents: {e}")

    yield

    # Shutdown
    logger.info("Shutting down")


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
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.api import chat_router, health_router

    app.include_router(health_router)
    app.include_router(chat_router)

    return app


app = create_app()
