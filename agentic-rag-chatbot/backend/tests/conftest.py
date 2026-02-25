import os

import pytest
from httpx import AsyncClient, ASGITransport

# テスト環境では安全なデフォルト値を設定する（モジュールインポート前に設定が必要）
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("DEBUG_MODE", "true")

from app.auth.jwt_handler import create_access_token  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def auth_headers() -> dict:
    """テスト用 JWT トークンのヘッダーを返す"""
    token = create_access_token({"sub": "test-user"})
    return {"Authorization": f"Bearer {token}"}
