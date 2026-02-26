"""画像添付API テストスイート

TDD RED フェーズ: 画像アップロード・バリデーションのテスト
"""

import base64
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.auth.jwt_handler import create_access_token


@pytest.fixture
def auth_headers() -> dict:
    """テスト用 JWT トークンのヘッダーを返す"""
    token = create_access_token({"sub": "test-user"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_image_base64() -> str:
    """テスト用の小さなPNG画像（Base64エンコード）"""
    # 1x1 pixel red PNG
    png_bytes = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR length + type
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,  # 8-bit RGB
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0x0F, 0x00, 0x00,
        0x01, 0x01, 0x01, 0x00, 0x18, 0xDD, 0x8D, 0xB4,
        0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44,  # IEND
        0xAE, 0x42, 0x60, 0x82
    ])
    return base64.b64encode(png_bytes).decode('utf-8')


class TestImageValidation:
    """画像バリデーションのテスト"""

    @pytest.mark.asyncio
    async def test_valid_image_upload(self, auth_headers, sample_image_base64):
        """有効な画像をアップロードできる"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat/image",
                headers=auth_headers,
                json={
                    "image_data": sample_image_base64,
                    "filename": "test.png",
                    "mime_type": "image/png"
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "image_id" in data["data"]

    @pytest.mark.asyncio
    async def test_invalid_image_format(self, auth_headers):
        """無効な画像形式は拒否される"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat/image",
                headers=auth_headers,
                json={
                    "image_data": "dGVzdA==",  # "test" in base64
                    "filename": "test.txt",
                    "mime_type": "text/plain"
                }
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_image_too_large(self, auth_headers):
        """サイズ超過の画像は拒否される"""
        # 11MB以上のデータを作成（Base64エンコード後）
        large_data = "A" * (11 * 1024 * 1024)
        large_base64 = base64.b64encode(large_data.encode()).decode('utf-8')
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat/image",
                headers=auth_headers,
                json={
                    "image_data": large_base64,
                    "filename": "large.png",
                    "mime_type": "image/png"
                }
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_unsupported_format(self, auth_headers):
        """サポートされていない画像形式は拒否される"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat/image",
                headers=auth_headers,
                json={
                    "image_data": "dGVzdA==",
                    "filename": "test.bmp",
                    "mime_type": "image/bmp"
                }
            )
            assert response.status_code == 422


class TestChatRequestWithImage:
    """画像付きチャットリクエストのテスト"""

    @pytest.mark.asyncio
    async def test_chat_with_image(self, auth_headers, sample_image_base64):
        """画像付きでチャットを開始できる"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat",
                headers=auth_headers,
                json={
                    "message": "この画像のエラーを教えてください",
                    "image_data": sample_image_base64
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "thread_id" in data["data"]

    @pytest.mark.asyncio
    async def test_chat_without_image_still_works(self, auth_headers):
        """画像なしのチャットも引き続き動作する"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat",
                headers=auth_headers,
                json={
                    "message": "こんにちは"
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
