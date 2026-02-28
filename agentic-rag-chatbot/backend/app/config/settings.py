import warnings
from functools import lru_cache

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings

_DEFAULT_JWT_SECRET = "dev-secret-key-change-in-production"
_DEFAULT_DATABASE_URL = "postgresql://chatbot_user:chatbot_password@localhost:5432/chatbot_db"


class Settings(BaseSettings):
    app_version: str = "0.4.0"
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4o-mini"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    cors_allowed_methods: list[str] = ["GET", "POST", "OPTIONS"]
    cors_allowed_headers: list[str] = ["Authorization", "Content-Type"]
    chroma_persist_dir: str = "./data/chroma_db"
    chroma_collection_name: str = "product_support_v2"
    embedding_model: str = "intfloat/multilingual-e5-base"
    jwt_secret_key: SecretStr = SecretStr(_DEFAULT_JWT_SECRET)
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
    retrieval_strategy: str = "standard"  # "standard" | "multi_query" | "hyde" | "hybrid"
    multi_query_count: int = 3  # Number of queries to generate in Multi-Query
    # Cross-Encoder Reranker settings
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_enabled: bool = True
    reranker_top_k: int = 5
    # PostgreSQL settings for PostgresSaver
    database_url: str = _DEFAULT_DATABASE_URL
    database_pool_size: int = 5
    database_max_overflow: int = 10

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @model_validator(mode="after")
    def validate_secrets(self) -> "Settings":
        """シークレット値の安全性を検証する。"""
        jwt_value = self.jwt_secret_key.get_secret_value()
        if jwt_value == _DEFAULT_JWT_SECRET:
            if not self.debug_mode:
                raise ValueError(
                    "JWT_SECRET_KEY にデフォルト値が使用されています。"
                    "本番環境では必ず安全なシークレットキーを設定してください。"
                )
            warnings.warn(
                "JWT_SECRET_KEY にデフォルト値が使用されています。"
                "本番環境では必ず安全なシークレットキーを設定してください。",
                UserWarning,
                stacklevel=2,
            )

        if self.database_url == _DEFAULT_DATABASE_URL:
            warnings.warn(
                "DATABASE_URL にデフォルト認証情報が使用されています。"
                "本番環境では必ず安全な認証情報を設定してください。",
                UserWarning,
                stacklevel=2,
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
