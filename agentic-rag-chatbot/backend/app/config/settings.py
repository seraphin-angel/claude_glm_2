from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_version: str = "0.1.0"
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4o-mini"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    cors_allowed_methods: list[str] = ["GET", "POST", "OPTIONS"]
    cors_allowed_headers: list[str] = ["Authorization", "Content-Type"]
    chroma_persist_dir: str = "./data/chroma_db"
    chroma_collection_name: str = "product_support_v2"
    embedding_model: str = "intfloat/multilingual-e5-base"
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    rate_limit_chat: str = "20/minute"
    rate_limit_stream: str = "30/minute"
    debug_mode: bool = False
    chunk_size: int = 800
    chunk_overlap: int = 100
    hybrid_search_alpha: float = 0.7
    bm25_top_k: int = 10
    relevance_skip_threshold: float = 0.85

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
