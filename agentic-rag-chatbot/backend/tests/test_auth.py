"""JWT 認証のテスト"""

from datetime import timedelta

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.jwt_handler import create_access_token, verify_token


class TestCreateAccessToken:
    def test_creates_valid_token(self):
        """有効なトークンが生成されること"""
        token = create_access_token({"sub": "test-user"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_creates_token_with_custom_expiry(self):
        """カスタム有効期限のトークンが生成されること"""
        token = create_access_token(
            {"sub": "test-user"},
            expires_delta=timedelta(minutes=5),
        )
        assert isinstance(token, str)


class TestVerifyToken:
    async def test_verify_valid_token(self):
        """有効なトークンが検証できること"""
        token = create_access_token({"sub": "test-user", "role": "admin"})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        payload = await verify_token(credentials)
        assert payload["sub"] == "test-user"
        assert payload["role"] == "admin"

    async def test_verify_expired_token(self):
        """期限切れトークンで HTTPException が発生すること"""
        token = create_access_token(
            {"sub": "test-user"},
            expires_delta=timedelta(seconds=-1),
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc_info:
            await verify_token(credentials)
        assert exc_info.value.status_code == 401

    async def test_verify_invalid_token(self):
        """不正なトークンで HTTPException が発生すること"""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid.token.string"
        )

        with pytest.raises(HTTPException) as exc_info:
            await verify_token(credentials)
        assert exc_info.value.status_code == 401

    async def test_verify_tampered_token(self):
        """改竄されたトークンで HTTPException が発生すること"""
        token = create_access_token({"sub": "test-user"})
        tampered = token[:-5] + "XXXXX"
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=tampered
        )

        with pytest.raises(HTTPException) as exc_info:
            await verify_token(credentials)
        assert exc_info.value.status_code == 401
