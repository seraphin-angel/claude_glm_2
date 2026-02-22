import pytest
from httpx import AsyncClient, ASGITransport

from app.auth.jwt_handler import create_access_token
from app.main import app


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
