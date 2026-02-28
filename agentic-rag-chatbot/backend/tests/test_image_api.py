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


class TestImageUploadEdgeCases:
    """画像アップロードのエッジケース（Criticality: 7-8）"""

    @pytest.mark.asyncio
    async def test_image_upload_size_limit_exactly_10mb(self, auth_headers):
        """10MB境界の画像サイズテスト"""
        # PNGヘッダー + 10MBデータ（境界値テスト）
        png_header = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
        # ヘッダー分を除いて10MBちょうどにする
        exact_10mb = png_header + b"\x00" * (10 * 1024 * 1024 - len(png_header))
        base64_10mb = base64.b64encode(exact_10mb).decode('utf-8')

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat/image",
                headers=auth_headers,
                json={
                    "image_data": base64_10mb,
                    "filename": "boundary.png",
                    "mime_type": "image/png"
                }
            )
            # 10MBちょうどは許可される
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_image_upload_invalid_base64_characters(self, auth_headers):
        """無効なBase64文字でエラーが返されること"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat/image",
                headers=auth_headers,
                json={
                    "image_data": "!!!invalid!!!base64!!!",
                    "filename": "invalid.txt",
                    "mime_type": "image/png"
                }
            )
            assert response.status_code == 422
            data = response.json()
            assert "Base64" in str(data) or "無効" in str(data)

    @pytest.mark.asyncio
    async def test_image_upload_empty_base64(self, auth_headers):
        """空のBase64データでエラーが返されること"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat/image",
                headers=auth_headers,
                json={
                    "image_data": "",
                    "filename": "empty.png",
                    "mime_type": "image/png"
                }
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_image_upload_invalid_mime_type_svg(self, auth_headers):
        """SVGはサポートされていないMIMEタイプとして拒否されること"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat/image",
                headers=auth_headers,
                json={
                    "image_data": base64.b64encode(b"<svg></svg>").decode('utf-8'),
                    "filename": "test.svg",
                    "mime_type": "image/svg+xml"
                }
            )
            assert response.status_code == 422
            data = response.json()
            # エラーメッセージにサポート形式が含まれることを確認
            assert "サポート" in str(data) or "形式" in str(data)

    @pytest.mark.asyncio
    async def test_image_upload_case_insensitive_mime_type(self, auth_headers, sample_image_base64):
        """MIMEタイプが大文字でも受け入れられること"""
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
                    "mime_type": "IMAGE/PNG"  # 大文字
                }
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_request_with_invalid_base64_image(self, auth_headers):
        """ChatRequestで無効なBase64画像を送るとエラーになること"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat",
                headers=auth_headers,
                json={
                    "message": "画像を見て",
                    "image_data": "not-valid-base64!!!"
                }
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_chat_request_with_oversized_image(self, auth_headers):
        """ChatRequestで10MB超過の画像を送るとエラーになること"""
        # 11MBのデータ
        oversized = b"\x00" * (11 * 1024 * 1024)
        oversized_base64 = base64.b64encode(oversized).decode('utf-8')

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat",
                headers=auth_headers,
                json={
                    "message": "大きな画像を見て",
                    "image_data": oversized_base64
                }
            )
            assert response.status_code == 422
            data = response.json()
            assert "大きすぎます" in str(data) or "10MB" in str(data)


class TestImageMagicBytesValidation:
    """画像マジックバイト検証のテスト（セキュリティ: 不正ファイルアップロード防止）"""

    @pytest.mark.asyncio
    async def test_upload_rejects_png_with_invalid_magic_bytes(self, auth_headers):
        """PNGヘッダーがないファイルを拒否する"""
        # MIMEタイプはimage/pngだが、実態はテキストファイル
        fake_png = base64.b64encode(b"Not a PNG file").decode()
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat/image",
                headers=auth_headers,
                json={
                    "image_data": fake_png,
                    "filename": "fake.png",
                    "mime_type": "image/png"
                }
            )
            assert response.status_code == 422
            data = response.json()
            assert "Invalid image format" in str(data) or "マジックバイト" in str(data)

    @pytest.mark.asyncio
    async def test_upload_rejects_jpeg_with_invalid_magic_bytes(self, auth_headers):
        """JPEGヘッダーがないファイルを拒否する"""
        fake_jpeg = base64.b64encode(b"Not a JPEG file").decode()
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat/image",
                headers=auth_headers,
                json={
                    "image_data": fake_jpeg,
                    "filename": "fake.jpg",
                    "mime_type": "image/jpeg"
                }
            )
            assert response.status_code == 422
            data = response.json()
            assert "Invalid image format" in str(data) or "マジックバイト" in str(data)

    @pytest.mark.asyncio
    async def test_upload_accepts_valid_png_magic_bytes(self, auth_headers):
        """有効なPNGヘッダーを持つファイルを受け入れる"""
        # PNGマジックバイト: 89 50 4E 47 0D 0A 1A 0A
        png_header = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
        minimal_png = png_header + b"\x00" * 100  # 最小限のPNG
        valid_png = base64.b64encode(minimal_png).decode()
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat/image",
                headers=auth_headers,
                json={
                    "image_data": valid_png,
                    "filename": "valid.png",
                    "mime_type": "image/png"
                }
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_upload_accepts_valid_jpeg_magic_bytes(self, auth_headers):
        """有効なJPEGヘッダーを持つファイルを受け入れる"""
        # JPEGマジックバイト: FF D8 FF
        jpeg_header = bytes([0xFF, 0xD8, 0xFF])
        minimal_jpeg = jpeg_header + b"\x00" * 100
        valid_jpeg = base64.b64encode(minimal_jpeg).decode()
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat/image",
                headers=auth_headers,
                json={
                    "image_data": valid_jpeg,
                    "filename": "valid.jpg",
                    "mime_type": "image/jpeg"
                }
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_upload_rejects_executable_disguised_as_png(self, auth_headers):
        """実行可能ファイルをPNGとしてアップロード攻撃を防ぐ"""
        # MZヘッダー (Windows実行ファイル)
        mz_header = b"MZ\x90\x00"  # DOS stub
        malicious = base64.b64encode(mz_header + b"\x00" * 100).decode()
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat/image",
                headers=auth_headers,
                json={
                    "image_data": malicious,
                    "filename": "malware.png",
                    "mime_type": "image/png"
                }
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_rejects_script_disguised_as_image(self, auth_headers):
        """スクリプトファイルを画像としてアップロード攻撃を防ぐ"""
        # HTML/JavaScriptを画像に偽装
        script_content = b"<script>alert('xss')</script>"
        malicious = base64.b64encode(script_content).decode()
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat/image",
                headers=auth_headers,
                json={
                    "image_data": malicious,
                    "filename": "xss.png",
                    "mime_type": "image/png"
                }
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_accepts_valid_gif_magic_bytes(self, auth_headers):
        """有効なGIFヘッダーを持つファイルを受け入れる"""
        # GIFマジックバイト: GIF89a
        gif_header = b"GIF89a"
        minimal_gif = gif_header + b"\x00" * 100
        valid_gif = base64.b64encode(minimal_gif).decode()
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat/image",
                headers=auth_headers,
                json={
                    "image_data": valid_gif,
                    "filename": "valid.gif",
                    "mime_type": "image/gif"
                }
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_upload_accepts_valid_webp_magic_bytes(self, auth_headers):
        """有効なWebPヘッダーを持つファイルを受け入れる"""
        # WebPマジックバイト: RIFF....WEBP
        webp_header = b"RIFF\x00\x00\x00\x00WEBP"
        minimal_webp = webp_header + b"\x00" * 100
        valid_webp = base64.b64encode(minimal_webp).decode()
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat/image",
                headers=auth_headers,
                json={
                    "image_data": valid_webp,
                    "filename": "valid.webp",
                    "mime_type": "image/webp"
                }
            )
            assert response.status_code == 200
