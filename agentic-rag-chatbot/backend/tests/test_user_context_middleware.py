"""UserContextMiddleware のテスト — X-User-IDヘッダー偽装修正"""

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

# JWT_SECRET_KEY, DEBUG_MODE は conftest.py で一元管理

from app.auth.jwt_handler import create_access_token  # noqa: E402
from app.middleware.user_context import (  # noqa: E402
    UserContextMiddleware,
    get_current_user_id,
    reset_user_context,
)


def _make_app() -> FastAPI:
    """テスト用の最小 FastAPI アプリを作成する。"""
    test_app = FastAPI()
    test_app.add_middleware(UserContextMiddleware)

    @test_app.get("/whoami")
    async def whoami(request: Request):
        user_id = get_current_user_id()
        return JSONResponse({"user_id": user_id})

    return test_app


@pytest.fixture
def app():
    return _make_app()


@pytest.fixture
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


class TestMiddlewareIgnoresXUserIdHeader:
    """X-User-ID ヘッダーを直接信頼しないことを確認する。"""

    async def test_middleware_ignores_x_user_id_header(self, client):
        """X-User-IDヘッダーが付いていてもコンテキストに設定されない。"""
        response = await client.get(
            "/whoami",
            headers={"X-User-ID": "evil-attacker-user-id"},
        )
        assert response.status_code == 200
        data = response.json()
        # X-User-ID ヘッダーの値はコンテキストに設定されないため None になること
        assert data["user_id"] is None


class TestMiddlewareExtractsUserIdFromJwt:
    """Authorization ヘッダーの有効な JWT からユーザーIDを抽出することを確認する。"""

    async def test_middleware_extracts_user_id_from_jwt(self, client):
        """Authorization: BearerヘッダーのJWTからユーザーIDを抽出する。"""
        token = create_access_token({"sub": "user-123"})
        response = await client.get(
            "/whoami",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "user-123"

    async def test_middleware_extracts_user_id_with_x_user_id_also_present(self, client):
        """X-User-IDと有効なJWTが両方あるとき、JWTのsubが採用される。"""
        token = create_access_token({"sub": "legit-user"})
        response = await client.get(
            "/whoami",
            headers={
                "Authorization": f"Bearer {token}",
                "X-User-ID": "evil-attacker-user-id",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "legit-user"


class TestMiddlewareResetsContextOnInvalidJwt:
    """無効な JWT の場合はコンテキスト未設定（None）になることを確認する。"""

    async def test_middleware_resets_context_on_invalid_jwt(self, client):
        """無効なJWTの場合はコンテキストが None になる。"""
        response = await client.get(
            "/whoami",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] is None

    async def test_middleware_resets_context_on_tampered_jwt(self, client):
        """改竄されたJWTの場合もコンテキストが None になる。"""
        token = create_access_token({"sub": "user-999"})
        tampered = token[:-5] + "XXXXX"
        response = await client.get(
            "/whoami",
            headers={"Authorization": f"Bearer {tampered}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] is None


class TestMiddlewareResetsContextNoAuthHeader:
    """Authorization ヘッダーなしの場合はコンテキスト未設定になることを確認する。"""

    async def test_middleware_resets_context_no_auth_header(self, client):
        """Authorizationヘッダーなしの場合はコンテキストが None になる。"""
        response = await client.get("/whoami")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] is None


class TestMiddlewareResetsContextAfterRequest:
    """リクエスト完了後にコンテキストがリセットされることを確認する。"""

    async def test_middleware_resets_context_after_request(self, app):
        """リクエスト完了後にコンテキストが None にリセットされる。"""
        token = create_access_token({"sub": "user-cleanup-test"})

        # リクエスト実行前はコンテキストが None
        assert get_current_user_id() is None

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            response = await ac.get(
                "/whoami",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        assert response.json()["user_id"] == "user-cleanup-test"

        # リクエスト完了後はコンテキストが None にリセットされている
        assert get_current_user_id() is None
