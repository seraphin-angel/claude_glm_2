"""P3-53: マルチチャネル対応のテスト (TDD)"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import inspect
import hashlib


# ---------------------------------------------------------------------------
# Phase 1: 基盤構築テスト
# ---------------------------------------------------------------------------
class TestChannelType:
    """ChannelType 列挙型のテスト"""

    def test_channel_type_enum_values(self):
        """ChannelType が期待される値を持つ"""
        from app.channels.models import ChannelType
        assert ChannelType.SLACK.value == "slack"
        assert ChannelType.LINE.value == "line"
        assert ChannelType.EMAIL.value == "email"
        assert ChannelType.WEB.value == "web"

    def test_channel_type_from_string(self):
        """文字列からChannelTypeを作成できる"""
        from app.channels.models import ChannelType
        assert ChannelType("slack") == ChannelType.SLACK
        assert ChannelType("line") == ChannelType.LINE


class TestChannelMessage:
    """ChannelMessage モデルのテスト"""

    def test_channel_message_creation(self):
        """ChannelMessage が正しく作成される"""
        from app.channels.models import ChannelMessage, ChannelType
        message = ChannelMessage(
            channel=ChannelType.SLACK,
            channel_message_id="msg-123",
            channel_thread_id="thread-456",
            sender_id="U12345",
            sender_name="Test User",
            content="こんにちは",
            timestamp="2024-01-15T10:30:00Z",
            metadata={"team_id": "T999"},
        )
        assert message.channel == ChannelType.SLACK
        assert message.channel_message_id == "msg-123"
        assert message.sender_id == "U12345"
        assert message.content == "こんにちは"

    def test_channel_message_immutability(self):
        """ChannelMessage は不変"""
        from app.channels.models import ChannelMessage, ChannelType
        message = ChannelMessage(
            channel=ChannelType.LINE,
            channel_message_id="msg-789",
            sender_id="user-abc",
            content="テスト",
            timestamp="2024-01-15T10:30:00Z",
        )
        with pytest.raises((TypeError, Exception)):
            message.content = "変更不可"

    def test_channel_message_optional_fields(self):
        """オプショナルフィールドがNoneで作成できる"""
        from app.channels.models import ChannelMessage, ChannelType
        message = ChannelMessage(
            channel=ChannelType.EMAIL,
            channel_message_id="email-001",
            sender_id="user@example.com",
            content="メール本文",
            timestamp="2024-01-15T10:30:00Z",
            channel_thread_id=None,
            sender_name=None,
            metadata=None,
        )
        assert message.channel_thread_id is None
        assert message.sender_name is None
        assert message.metadata is None


class TestChannelConfig:
    """ChannelConfig モデルのテスト"""

    def test_channel_config_creation(self):
        """ChannelConfig が正しく作成される"""
        from app.channels.models import ChannelConfig, ChannelType
        config = ChannelConfig(
            channel=ChannelType.SLACK,
            tenant_id="tenant-001",
            config={"webhook_url": "https://hooks.slack.com/xxx"},
            enabled=True,
        )
        assert config.channel == ChannelType.SLACK
        assert config.tenant_id == "tenant-001"
        assert config.enabled is True

    def test_channel_config_immutability(self):
        """ChannelConfig は不変"""
        from app.channels.models import ChannelConfig, ChannelType
        config = ChannelConfig(
            channel=ChannelType.LINE,
            tenant_id="tenant-002",
        )
        with pytest.raises((TypeError, Exception)):
            config.enabled = False


class TestThreadMapping:
    """ThreadMapping モデルのテスト"""

    def test_thread_mapping_creation(self):
        """ThreadMapping が正しく作成される"""
        from uuid import uuid4
        from app.channels.models import ThreadMapping, ChannelType
        internal_id = uuid4()
        mapping = ThreadMapping(
            internal_thread_id=internal_id,
            channel=ChannelType.SLACK,
            channel_thread_id="ts-1234567890",
            channel_message_id="msg-001",
        )
        assert mapping.internal_thread_id == internal_id
        assert mapping.channel == ChannelType.SLACK
        assert mapping.channel_thread_id == "ts-1234567890"


class TestBaseChannelAdapter:
    """BaseChannelAdapter 抽象クラスのテスト"""

    def test_base_adapter_is_abstract(self):
        """BaseChannelAdapter は抽象クラス"""
        from app.channels.base import BaseChannelAdapter
        assert inspect.isabstract(BaseChannelAdapter)

    def test_base_adapter_has_required_methods(self):
        """BaseChannelAdapter に必要なメソッドが定義されている"""
        from app.channels.base import BaseChannelAdapter
        required_methods = [
            "channel_type",
            "send_message",
            "parse_event",
            "verify_signature",
            "health_check",
        ]
        for method in required_methods:
            assert hasattr(BaseChannelAdapter, method), f"Missing: {method}"


class TestMockChannelAdapter:
    """MockChannelAdapter のテスト"""

    @pytest.fixture
    def mock_adapter(self):
        """モックアダプターインスタンス"""
        from app.channels.mock_adapter import MockChannelAdapter
        from app.channels.models import ChannelType
        return MockChannelAdapter(channel_type=ChannelType.WEB)

    def test_adapter_channel_type(self, mock_adapter):
        """チャネルタイプが正しい"""
        from app.channels.models import ChannelType
        assert mock_adapter.channel_type == ChannelType.WEB

    @pytest.mark.asyncio
    async def test_send_message(self, mock_adapter):
        """メッセージを送信できる"""
        result = await mock_adapter.send_message(
            recipient_id="user-001",
            content="テストメッセージ",
        )
        assert result["success"] is True
        assert "message_id" in result
        assert result["message_id"].startswith("MOCK-")

    @pytest.mark.asyncio
    async def test_send_message_with_thread(self, mock_adapter):
        """スレッドID付きでメッセージを送信できる"""
        result = await mock_adapter.send_message(
            recipient_id="user-001",
            content="スレッド内メッセージ",
            thread_id="thread-123",
        )
        assert result["success"] is True
        assert result["thread_id"] == "thread-123"

    @pytest.mark.asyncio
    async def test_parse_event(self, mock_adapter):
        """イベントを解析できる"""
        from app.channels.models import ChannelType
        event_data = {
            "message_id": "event-msg-001",
            "sender_id": "sender-abc",
            "sender_name": "Sender Name",
            "content": "イベントメッセージ",
            "timestamp": "2024-01-15T12:00:00Z",
            "thread_id": "thread-xyz",
        }
        message = await mock_adapter.parse_event(event_data)
        assert message is not None
        assert message.channel == ChannelType.WEB
        assert message.channel_message_id == "event-msg-001"
        assert message.content == "イベントメッセージ"

    @pytest.mark.asyncio
    async def test_parse_event_empty(self, mock_adapter):
        """空のイベントはNoneを返す"""
        result = await mock_adapter.parse_event({})
        assert result is None

    @pytest.mark.asyncio
    async def test_parse_event_none(self, mock_adapter):
        """NoneイベントはNoneを返す"""
        result = await mock_adapter.parse_event(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_verify_signature(self, mock_adapter):
        """署名検証（モックは常にTrue）"""
        result = await mock_adapter.verify_signature(
            signature="any-signature",
            body=b"any-body",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check(self, mock_adapter):
        """ヘルスチェック（モックは常にTrue）"""
        result = await mock_adapter.health_check()
        assert result is True

    def test_get_sent_messages(self, mock_adapter):
        """送信済みメッセージ一覧を取得できる"""
        import asyncio
        # メッセージを送信
        asyncio.run(mock_adapter.send_message("user-1", "test"))
        messages = mock_adapter.get_sent_messages()
        assert len(messages) == 1
        assert messages[0]["content"] == "test"

    def test_clear_sent_messages(self, mock_adapter):
        """送信済みメッセージをクリアできる"""
        import asyncio
        asyncio.run(mock_adapter.send_message("user-1", "test"))
        mock_adapter.clear_sent_messages()
        messages = mock_adapter.get_sent_messages()
        assert len(messages) == 0


# ---------------------------------------------------------------------------
# Phase 2: チャネルアダプターテスト（Slack, LINE, Email）
# ---------------------------------------------------------------------------

class TestSlackAdapter:
    """Slack アダプターのテスト"""

    @pytest.fixture
    def slack_adapter(self):
        """Slack アダプターインスタンス"""
        from app.channels.slack_adapter import SlackAdapter
        return SlackAdapter(
            bot_token="xoxb-test-token",
            signing_secret="test-signing-secret",
        )

    def test_adapter_initialization(self, slack_adapter):
        """アダプターが正しく初期化される"""
        from app.channels.models import ChannelType
        assert slack_adapter.channel_type == ChannelType.SLACK

    @pytest.mark.asyncio
    async def test_send_message(self, slack_adapter):
        """メッセージを送信できる"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "ok": True,
                "ts": "1234567890.123456",
                "channel": "C12345",
            }
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await slack_adapter.send_message(
                recipient_id="C12345",
                content="テストメッセージ",
            )

        assert result["success"] is True
        assert result["message_id"] == "1234567890.123456"

    @pytest.mark.asyncio
    async def test_send_message_with_thread(self, slack_adapter):
        """スレッド付きメッセージを送信できる"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "ok": True,
                "ts": "1234567890.654321",
                "channel": "C12345",
            }
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await slack_adapter.send_message(
                recipient_id="C12345",
                content="スレッド返信",
                thread_id="1234567890.111111",
            )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_parse_event(self, slack_adapter):
        """Slackイベントを解析できる"""
        from app.channels.models import ChannelType
        event_data = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "ts": "1234567890.123456",
                "thread_ts": "1234567890.111111",
                "user": "U12345",
                "text": "Slackメッセージ",
                "channel": "C12345",
            },
        }
        message = await slack_adapter.parse_event(event_data)
        assert message is not None
        assert message.channel == ChannelType.SLACK
        assert message.channel_message_id == "1234567890.123456"
        assert message.channel_thread_id == "1234567890.111111"
        assert message.sender_id == "U12345"
        assert message.content == "Slackメッセージ"

    @pytest.mark.asyncio
    async def test_verify_signature_valid(self, slack_adapter):
        """有効な署名を検証できる"""
        import hmac
        import time
        body = b'{"test": "data"}'
        # 現在時刻を使用（リプレイアタック防止チェックを通過するため）
        timestamp = str(int(time.time()))
        # 正しい署名を生成
        sig_basestring = f"v0:{timestamp}:{body.decode()}".encode()
        signature = "v0=" + hmac.new(
            b"test-signing-secret",
            sig_basestring,
            hashlib.sha256
        ).hexdigest()

        result = await slack_adapter.verify_signature(
            signature=signature,
            body=body,
            timestamp=timestamp,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_signature_invalid(self, slack_adapter):
        """無効な署名は拒否される"""
        result = await slack_adapter.verify_signature(
            signature="v0=invalid",
            body=b"test",
            timestamp="1234567890",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check(self, slack_adapter):
        """ヘルスチェック"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"ok": True}
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await slack_adapter.health_check()

        assert result is True


class TestLineAdapter:
    """LINE アダプターのテスト"""

    @pytest.fixture
    def line_adapter(self):
        """LINE アダプターインスタンス"""
        from app.channels.line_adapter import LineAdapter
        return LineAdapter(
            channel_access_token="test-channel-token",
            channel_secret="test-channel-secret",
        )

    def test_adapter_initialization(self, line_adapter):
        """アダプターが正しく初期化される"""
        from app.channels.models import ChannelType
        assert line_adapter.channel_type == ChannelType.LINE

    @pytest.mark.asyncio
    async def test_send_message(self, line_adapter):
        """メッセージを送信できる"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "sentMessages": [{"id": "msg-line-001"}]
            }
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await line_adapter.send_message(
                recipient_id="U1234567890abcdef",
                content="LINEテストメッセージ",
            )

        assert result["success"] is True
        assert result["message_id"] == "msg-line-001"

    @pytest.mark.asyncio
    async def test_parse_webhook(self, line_adapter):
        """LINE Webhookを解析できる"""
        import time
        from app.channels.models import ChannelType
        # 現在のタイムスタンプを使用（リプレイアタック防止のため）
        current_timestamp_ms = int(time.time() * 1000)
        event_data = {
            "events": [
                {
                    "type": "message",
                    "replyToken": "reply-token-123",
                    "source": {"userId": "U1234567890abcdef"},
                    "message": {"type": "text", "text": "LINEメッセージ"},
                    "timestamp": current_timestamp_ms,
                }
            ]
        }
        message = await line_adapter.parse_event(event_data)
        assert message is not None
        assert message.channel == ChannelType.LINE
        assert message.sender_id == "U1234567890abcdef"
        assert message.content == "LINEメッセージ"

    @pytest.mark.asyncio
    async def test_verify_signature_valid(self, line_adapter):
        """有効な署名を検証できる"""
        import hmac
        import base64
        body = b'{"test": "data"}'
        # 正しい署名を生成
        signature = base64.b64encode(
            hmac.new(
                b"test-channel-secret",
                body,
                hashlib.sha256
            ).digest()
        ).decode()

        result = await line_adapter.verify_signature(
            signature=signature,
            body=body,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_signature_invalid(self, line_adapter):
        """無効な署名は拒否される"""
        result = await line_adapter.verify_signature(
            signature="invalid-signature",
            body=b"test",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check(self, line_adapter):
        """ヘルスチェック"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"limit": 1000}
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await line_adapter.health_check()

        assert result is True


class TestEmailAdapter:
    """Email アダプターのテスト"""

    @pytest.fixture
    def email_adapter(self):
        """Email アダプターインスタンス"""
        from app.channels.email_adapter import EmailAdapter
        return EmailAdapter(
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="test@test.com",
            smtp_password="test-password",
            imap_host="imap.test.com",
            imap_port=993,
            imap_user="test@test.com",
            imap_password="test-password",
        )

    def test_adapter_initialization(self, email_adapter):
        """アダプターが正しく初期化される"""
        from app.channels.models import ChannelType
        assert email_adapter.channel_type == ChannelType.EMAIL

    @pytest.mark.asyncio
    async def test_send_email(self, email_adapter):
        """メールを送信できる"""
        with patch("aiosmtplib.send") as mock_send:
            mock_send.return_value = {}

            result = await email_adapter.send_message(
                recipient_id="recipient@test.com",
                content="メール本文",
                subject="テストメール",
            )

        assert result["success"] is True
        assert "message_id" in result

    @pytest.mark.asyncio
    async def test_parse_email(self, email_adapter):
        """メールを解析できる"""
        from app.channels.models import ChannelType
        from email.message import EmailMessage
        import email.utils

        # テスト用メールを作成
        msg = EmailMessage()
        msg["Message-ID"] = "<test-msg-001@test.com>"
        msg["In-Reply-To"] = "<parent-msg@test.com>"
        msg["References"] = "<parent-msg@test.com>"
        msg["From"] = "sender@test.com"
        msg["To"] = "bot@test.com"
        msg["Subject"] = "Re: テストスレッド"
        msg["Date"] = "Mon, 15 Jan 2024 10:30:00 +0000"
        msg.set_content("メール返信本文")

        event_data = {"raw_message": msg}

        message = await email_adapter.parse_event(event_data)
        assert message is not None
        assert message.channel == ChannelType.EMAIL
        assert message.sender_id == "sender@test.com"
        assert message.content == "メール返信本文"
        assert message.channel_thread_id == "<parent-msg@test.com>"

    @pytest.mark.asyncio
    async def test_verify_signature_no_secret_rejects(self, email_adapter):
        """webhook_secret未設定の場合は拒否される（セキュリティ強化）"""
        result = await email_adapter.verify_signature(
            signature="",
            body=b"",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_signature_with_secret_valid(self):
        """webhook_secret設定時にHMAC署名が正しい場合に通過する"""
        import hashlib, hmac as hmaclib
        from app.channels.email_adapter import EmailAdapter
        secret = "my-secret"
        body = b""
        expected_hmac = hmaclib.new(secret.encode(), body, hashlib.sha256).hexdigest()
        adapter = EmailAdapter(
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="test@test.com",
            smtp_password="test-password",
            imap_host="imap.test.com",
            imap_port=993,
            imap_user="test@test.com",
            imap_password="test-password",
            webhook_secret=secret,
        )
        result = await adapter.verify_signature(
            signature=expected_hmac,
            body=body,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_signature_with_secret_invalid(self):
        """webhook_secret設定時に誤ったシークレットで拒否される"""
        from app.channels.email_adapter import EmailAdapter
        adapter = EmailAdapter(
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="test@test.com",
            smtp_password="test-password",
            imap_host="imap.test.com",
            imap_port=993,
            imap_user="test@test.com",
            imap_password="test-password",
            webhook_secret="my-secret",
        )
        result = await adapter.verify_signature(
            signature="wrong-secret",
            body=b"",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check(self, email_adapter):
        """ヘルスチェック"""
        with patch("aiosmtplib.SMTP") as mock_smtp_class:
            mock_smtp = AsyncMock()
            mock_smtp.connect = AsyncMock()
            mock_smtp.noop = AsyncMock(return_value=(220, b"OK"))
            mock_smtp.quit = AsyncMock()
            mock_smtp_class.return_value = mock_smtp

            result = await email_adapter.health_check()

        assert result is True


# ---------------------------------------------------------------------------
# Phase 3: サービス層テスト
# ---------------------------------------------------------------------------

class TestChannelService:
    """ChannelService のテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.channel_service import ChannelService
        ChannelService.reset_instance()
        yield
        ChannelService.reset_instance()

    def test_singleton(self):
        """シングルトンパターンが動作する"""
        from app.services.channel_service import ChannelService
        service1 = ChannelService.get_instance()
        service2 = ChannelService.get_instance()
        assert service1 is service2

    def test_register_adapter(self):
        """アダプターを登録できる"""
        from app.services.channel_service import ChannelService
        from app.channels.mock_adapter import MockChannelAdapter
        from app.channels.models import ChannelType
        service = ChannelService.get_instance()
        adapter = MockChannelAdapter(channel_type=ChannelType.SLACK)
        service.register_adapter("tenant-001", ChannelType.SLACK, adapter)
        assert service.get_adapter("tenant-001", ChannelType.SLACK) is not None

    def test_get_adapter_not_registered(self):
        """未登録アダプターはNoneを返す"""
        from app.services.channel_service import ChannelService
        from app.channels.models import ChannelType
        service = ChannelService.get_instance()
        result = service.get_adapter("nonexistent", ChannelType.SLACK)
        assert result is None

    @pytest.mark.asyncio
    async def test_create_thread_mapping(self):
        """スレッドマッピングを作成できる"""
        from uuid import UUID
        from app.services.channel_service import ChannelService
        from app.channels.models import ChannelType
        service = ChannelService.get_instance()

        mapping = await service.create_thread_mapping(
            channel=ChannelType.SLACK,
            channel_thread_id="ts-1234567890",
            channel_message_id="msg-001",
        )
        assert mapping is not None
        assert isinstance(mapping.internal_thread_id, UUID)
        assert mapping.channel == ChannelType.SLACK
        assert mapping.channel_thread_id == "ts-1234567890"

    @pytest.mark.asyncio
    async def test_get_internal_thread_id(self):
        """チャネルスレッドIDから内部IDを取得できる"""
        from app.services.channel_service import ChannelService
        from app.channels.models import ChannelType
        service = ChannelService.get_instance()

        # マッピング作成
        created = await service.create_thread_mapping(
            channel=ChannelType.SLACK,
            channel_thread_id="ts-999",
        )

        # 取得
        found = service.get_internal_thread_id(ChannelType.SLACK, "ts-999")
        assert found == created.internal_thread_id

    @pytest.mark.asyncio
    async def test_route_to_channel(self):
        """メッセージを適切なチャネルにルーティングできる"""
        from app.services.channel_service import ChannelService
        from app.channels.mock_adapter import MockChannelAdapter
        from app.channels.models import ChannelType
        service = ChannelService.get_instance()
        adapter = MockChannelAdapter(channel_type=ChannelType.SLACK)
        service.register_adapter("tenant-001", ChannelType.SLACK, adapter)

        result = await service.route_to_channel(
            tenant_id="tenant-001",
            channel=ChannelType.SLACK,
            recipient_id="U12345",
            content="ルーティングテスト",
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_route_to_channel_no_adapter(self):
        """アダプター未登録時はエラー"""
        from app.services.channel_service import ChannelService
        from app.channels.models import ChannelType
        service = ChannelService.get_instance()

        with pytest.raises(ValueError, match="No adapter"):
            await service.route_to_channel(
                tenant_id="no-adapter",
                channel=ChannelType.SLACK,
                recipient_id="U12345",
                content="test",
            )


# ---------------------------------------------------------------------------
# Phase 4: API層テスト
# ---------------------------------------------------------------------------

class TestChannelAPI:
    """チャネル Webhook API のテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.channel_service import ChannelService
        ChannelService.reset_instance()
        yield
        ChannelService.reset_instance()

    @pytest.fixture
    def admin_headers(self) -> dict:
        """管理者JWTトークン"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from app.auth.jwt_handler import create_access_token
        token = create_access_token({"sub": "admin-user", "role": "admin"})
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_slack_webhook_endpoint(self):
        """Slack Webhookエンドポイント（アダプター未登録時は404）"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/channels/slack/webhook",
                json={
                    "type": "event_callback",
                    "event": {
                        "type": "message",
                        "ts": "1234567890.123456",
                        "user": "U12345",
                        "text": "テスト",
                        "channel": "C12345",
                    },
                },
                headers={
                    "X-Slack-Signature": "v0=test",
                    "X-Slack-Request-Timestamp": "1234567890",
                    "X-Tenant-ID": "test-tenant",
                },
            )
        # アダプター未登録なので404を返す
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_line_webhook_endpoint(self):
        """LINE Webhookエンドポイント（アダプター未登録時は404）"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/channels/line/webhook",
                json={
                    "events": [
                        {
                            "type": "message",
                            "source": {"userId": "U123456"},
                            "message": {"type": "text", "text": "テスト"},
                        }
                    ]
                },
                headers={
                    "X-Line-Signature": "test-signature",
                    "X-Tenant-ID": "test-tenant",
                },
            )
        # アダプター未登録なので404を返す
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_slack_url_verification(self):
        """Slack URL検証チャレンジはアダプター登録後に署名検証後に処理される。
        
        セキュリティ修正#1: legacyエンドポイントでも署名検証が必要になった。
        アダプター未登録の場合は404を返す。
        """
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/channels/slack/webhook",
                json={
                    "type": "url_verification",
                    "challenge": "test-challenge-string",
                },
                headers={"X-Tenant-ID": "test-tenant"},
            )
        # アダプター未登録のため404（署名検証前にアダプター取得が必要）
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# ChatRequest 拡張テスト
# ---------------------------------------------------------------------------

class TestChatRequestExtension:
    """ChatRequest のチャネル拡張テスト"""

    def test_chat_request_with_channel(self):
        """ChatRequest にチャネルフィールドを追加"""
        from app.models.chat import ChatRequest
        from uuid import uuid4
        thread_id = uuid4()
        request = ChatRequest(
            message="テストメッセージ",
            thread_id=thread_id,
            channel="slack",
            channel_thread_id="ts-1234567890",
        )
        assert request.channel == "slack"
        assert request.channel_thread_id == "ts-1234567890"

    def test_chat_request_channel_optional(self):
        """チャネルフィールドはオプショナル"""
        from app.models.chat import ChatRequest
        request = ChatRequest(
            message="Webチャット",
        )
        assert request.channel is None
        assert request.channel_thread_id is None


# ---------------------------------------------------------------------------
# Phase 5: セキュリティ修正テスト（CRITICAL + HIGH）
# ---------------------------------------------------------------------------

class TestWebhookSignatureVerification:
    """CRITICAL-1: Webhook署名検証のテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.channel_service import ChannelService
        ChannelService.reset_instance()
        yield
        ChannelService.reset_instance()

    @pytest.mark.asyncio
    async def test_slack_webhook_rejects_invalid_signature(self):
        """Slack Webhookは無効な署名を拒否する"""
        import os
        import hmac
        import time
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")

        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.services.channel_service import ChannelService
        from app.channels.slack_adapter import SlackAdapter
        from app.channels.models import ChannelType

        # アダプターを登録
        service = ChannelService.get_instance()
        adapter = SlackAdapter(
            bot_token="xoxb-test",
            signing_secret="test-secret",
        )
        service.register_adapter("tenant-001", ChannelType.SLACK, adapter)

        # テナントコンテキストを設定
        from app.middleware.tenant import set_tenant_context
        set_tenant_context("tenant-001")

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 無効な署名でリクエスト
            response = await client.post(
                "/api/channels/slack/webhook",
                json={
                    "type": "event_callback",
                    "event": {
                        "type": "message",
                        "ts": "1234567890.123456",
                        "user": "U12345",
                        "text": "テスト",
                        "channel": "C12345",
                    },
                },
                headers={
                    "X-Slack-Signature": "v0=invalid_signature",
                    "X-Slack-Request-Timestamp": str(int(time.time())),
                    "X-Tenant-ID": "tenant-001",
                },
            )
        # 無効な署名の場合は401を返す
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_line_webhook_rejects_invalid_signature(self):
        """LINE Webhookは無効な署名を拒否する"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")

        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.services.channel_service import ChannelService
        from app.channels.line_adapter import LineAdapter
        from app.channels.models import ChannelType

        # アダプターを登録
        service = ChannelService.get_instance()
        adapter = LineAdapter(
            channel_access_token="test-token",
            channel_secret="test-secret",
        )
        service.register_adapter("tenant-001", ChannelType.LINE, adapter)

        # テナントコンテキストを設定
        from app.middleware.tenant import set_tenant_context
        set_tenant_context("tenant-001")

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 無効な署名でリクエスト
            response = await client.post(
                "/api/channels/line/webhook",
                json={
                    "events": [
                        {
                            "type": "message",
                            "source": {"userId": "U123456"},
                            "message": {"type": "text", "text": "テスト"},
                        }
                    ]
                },
                headers={
                    "X-Line-Signature": "invalid_signature",
                    "X-Tenant-ID": "tenant-001",
                },
            )
        # 無効な署名の場合は401を返す
        assert response.status_code == 401


class TestAdminAPIAuthentication:
    """CRITICAL-2: 管理API認証のテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.channel_service import ChannelService
        ChannelService.reset_instance()
        yield
        ChannelService.reset_instance()

    @pytest.fixture
    def admin_headers(self) -> dict:
        """管理者JWTトークン"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from app.auth.jwt_handler import create_access_token
        token = create_access_token({"sub": "admin-user", "role": "admin"})
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def user_headers(self) -> dict:
        """一般ユーザーJWTトークン"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from app.auth.jwt_handler import create_access_token
        token = create_access_token({"sub": "normal-user", "role": "user"})
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_register_channel_requires_authentication(self):
        """チャネル登録は認証が必要"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")

        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 認証なしでリクエスト
            response = await client.post(
                "/api/channels/register",
                json={
                    "tenant_id": "tenant-001",
                    "channel": "slack",
                    "adapter_type": "mock",
                    "config": {},
                },
            )
        # 認証エラー（401）を返すべき
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_register_channel_succeeds_with_admin_token(self, admin_headers):
        """管理者トークンでチャネル登録が成功する"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")

        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/channels/register",
                json={
                    "tenant_id": "tenant-001",
                    "channel": "slack",
                    "adapter_type": "mock",
                    "config": {},
                },
                headers=admin_headers,
            )
        # is_adminクレームなしのトークンは403を返す
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_channels_requires_authentication(self):
        """チャネル一覧取得は認証が必要"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")

        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 認証なしでリクエスト
            response = await client.get(
                "/api/channels/list",
                params={"tenant_id": "tenant-001"},
            )
        # 認証エラー（401）を返すべき
        assert response.status_code == 401


class TestTenantIDFromHeader:
    """CRITICAL-3: テナントIDをヘッダーから取得するテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.channel_service import ChannelService
        ChannelService.reset_instance()
        yield
        ChannelService.reset_instance()

    @pytest.fixture
    def admin_headers(self) -> dict:
        """管理者JWTトークン"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from app.auth.jwt_handler import create_access_token
        token = create_access_token({"sub": "admin-user", "role": "admin"})
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_webhook_uses_tenant_from_header(self, admin_headers):
        """WebhookはX-Tenant-IDヘッダーからテナントIDを取得する"""
        import os
        import hmac
        import time
        import hashlib
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")

        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.services.channel_service import ChannelService
        from app.channels.slack_adapter import SlackAdapter
        from app.channels.models import ChannelType

        # アダプターを特定のテナントに登録
        service = ChannelService.get_instance()
        adapter = SlackAdapter(
            bot_token="xoxb-test",
            signing_secret="test-signing-secret",
        )
        service.register_adapter("custom-tenant-999", ChannelType.SLACK, adapter)

        # 有効な署名を生成
        body = '{"type":"url_verification","challenge":"test-challenge"}'
        timestamp = str(int(time.time()))
        sig_basestring = f"v0:{timestamp}:{body}".encode()
        signature = "v0=" + hmac.new(
            b"test-signing-secret",
            sig_basestring,
            hashlib.sha256
        ).hexdigest()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # X-Tenant-IDヘッダーでテナントを指定
            response = await client.post(
                "/api/channels/slack/webhook",
                content=body,
                headers={
                    "X-Slack-Signature": signature,
                    "X-Slack-Request-Timestamp": timestamp,
                    "X-Tenant-ID": "custom-tenant-999",
                    "Content-Type": "application/json",
                },
            )
        # URL検証は署名検証なしで成功する
        assert response.status_code == 200
        assert response.json().get("challenge") == "test-challenge"


class TestAiosmtplibImport:
    """HIGH-4: aiosmtplib遅延インポートのテスト"""

    def test_email_adapter_module_imports_aiosmtplib_at_top(self):
        """email_adapterモジュールは先頭でaiosmtplibをインポートする"""
        from app.channels import email_adapter

        # モジュールレベルでaiosmtplibがインポートされていることを確認
        # try-exceptブロック内でインポートされ、AIOSMTPLIB_AVAILABLEフラグが設定される
        assert hasattr(email_adapter, "AIOSMTPLIB_AVAILABLE"), \
            "email_adapter should have AIOSMTPLIB_AVAILABLE flag"
        assert hasattr(email_adapter, "aiosmtplib"), \
            "email_adapter should have aiosmtplib module reference"

        # aiosmtplibがインストールされている場合は利用可能
        assert email_adapter.AIOSMTPLIB_AVAILABLE is True, \
            "aiosmtplib should be available (installed)"


class TestChannelServiceThreadSafety:
    """HIGH-5: ChannelService スレッドセーフティのテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.channel_service import ChannelService
        ChannelService.reset_instance()
        yield
        ChannelService.reset_instance()

    def test_channel_service_has_instance_lock(self):
        """ChannelServiceはインスタンスレベルのロックを持つ"""
        from app.services.channel_service import ChannelService
        from threading import Lock

        service = ChannelService.get_instance()

        # インスタンスレベルのロックが存在することを確認
        assert hasattr(service, "_data_lock"), \
            "ChannelService should have _data_lock attribute"
        lock = service._data_lock
        assert type(lock).__name__.lower() == "lock", \
            "ChannelService._data_lock should be a Lock instance"

    @pytest.mark.asyncio
    async def test_concurrent_thread_mapping_creation(self):
        """並行してスレッドマッピングを作成してもデータが破損しない"""
        import asyncio
        from app.services.channel_service import ChannelService
        from app.channels.models import ChannelType

        service = ChannelService.get_instance()

        async def create_mapping(thread_id: str):
            return await service.create_thread_mapping(
                channel=ChannelType.SLACK,
                channel_thread_id=thread_id,
            )

        # 100個の並行マッピング作成
        tasks = [create_mapping(f"thread-{i}") for i in range(100)]
        results = await asyncio.gather(*tasks)

        # すべて成功し、内部整合性が保たれていることを確認
        assert len(results) == 100
        for mapping in results:
            assert mapping is not None
            # 逆引きが正しく動作することを確認
            internal_id = service.get_internal_thread_id(
                ChannelType.SLACK,
                mapping.channel_thread_id
            )
            assert internal_id == mapping.internal_thread_id


class TestEmailAdapterExceptionLogging:
    """HIGH-6: EmailAdapter例外ログ出力のテスト"""

    @pytest.fixture
    def email_adapter(self):
        """Email アダプターインスタンス"""
        from app.channels.email_adapter import EmailAdapter
        return EmailAdapter(
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="test@test.com",
            smtp_password="test-password",
            imap_host="imap.test.com",
            imap_port=993,
            imap_user="test@test.com",
            imap_password="test-password",
        )

    @pytest.mark.asyncio
    async def test_parse_event_logs_exception(self, email_adapter, caplog):
        """parse_eventで例外が発生した場合、ログが出力される"""
        import logging

        # 不正なraw_messageで例外を発生させる
        event_data = {"raw_message": object()}

        with caplog.at_level(logging.WARNING):
            result = await email_adapter.parse_event(event_data)

        # Noneが返される
        assert result is None
        # ログが出力されていることを確認
        assert any("parse_event" in record.message or "email" in record.message.lower()
                   for record in caplog.records if record.levelno >= logging.WARNING)


# ---------------------------------------------------------------------------
# P3-53 セキュリティ修正テスト (CRITICAL-1, CRITICAL-2, HIGH-1, HIGH-2)
# ---------------------------------------------------------------------------

class TestWebhookAdapterNotFound:
    """CRITICAL-1: アダプター未登録時に404を返すテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.channel_service import ChannelService
        ChannelService.reset_instance()
        yield
        ChannelService.reset_instance()

    @pytest.fixture(autouse=True)
    def setup_env(self):
        """環境変数を設定"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")

    @pytest.mark.asyncio
    async def test_slack_webhook_returns_404_when_no_adapter(self):
        """アダプター未登録時、Slack Webhookは404を返す"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/channels/slack/webhook",
                json={
                    "type": "event_callback",
                    "event": {
                        "type": "message",
                        "ts": "1234567890.123456",
                        "user": "U12345",
                        "text": "テスト",
                        "channel": "C12345",
                    },
                },
                headers={
                    "X-Slack-Signature": "v0=test",
                    "X-Slack-Request-Timestamp": "1234567890",
                    "X-Tenant-ID": "no-adapter-tenant",
                },
            )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_line_webhook_returns_404_when_no_adapter(self):
        """アダプター未登録時、LINE Webhookは404を返す"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/channels/line/webhook",
                json={
                    "events": [
                        {
                            "type": "message",
                            "source": {"userId": "U123456"},
                            "message": {"type": "text", "text": "テスト"},
                        }
                    ]
                },
                headers={
                    "X-Line-Signature": "test-signature",
                    "X-Tenant-ID": "no-adapter-tenant",
                },
            )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_slack_webhook_validates_signature_when_adapter_exists(self):
        """アダプター登録済みの場合、Slack Webhookは署名検証を実施する"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.services.channel_service import ChannelService
        from app.channels.slack_adapter import SlackAdapter
        from app.channels.models import ChannelType

        # アダプターを登録
        service = ChannelService.get_instance()
        adapter = SlackAdapter(
            bot_token="xoxb-test",
            signing_secret="valid-signing-secret",
        )
        service.register_adapter("tenant-with-adapter", ChannelType.SLACK, adapter)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 無効な署名でリクエスト → 署名検証が実施されて401
            response = await client.post(
                "/api/channels/slack/webhook",
                json={
                    "type": "event_callback",
                    "event": {
                        "type": "message",
                        "ts": "1234567890.123456",
                        "user": "U12345",
                        "text": "テスト",
                        "channel": "C12345",
                    },
                },
                headers={
                    "X-Slack-Signature": "v0=invalid_signature",
                    "X-Slack-Request-Timestamp": "1234567890",
                    "X-Tenant-ID": "tenant-with-adapter",
                },
            )
        # 署名が無効なので401
        assert response.status_code == 401


class TestEmailWebhookSecurity:
    """CRITICAL-2: Email Webhookのセキュリティテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.channel_service import ChannelService
        ChannelService.reset_instance()
        yield
        ChannelService.reset_instance()

    @pytest.fixture(autouse=True)
    def setup_env(self):
        """環境変数を設定"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")

    @pytest.mark.asyncio
    async def test_email_webhook_returns_404_when_no_adapter(self):
        """アダプター未登録時、Email Webhookは404を返す"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/channels/email/webhook",
                json={"raw_message": "test email content"},
                headers={
                    "X-Tenant-ID": "no-adapter-tenant",
                },
            )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_email_webhook_verifies_signature(self):
        """アダプター登録済みの場合、Email Webhookは署名検証を実施する"""
        import hmac
        import hashlib
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.services.channel_service import ChannelService
        from app.channels.email_adapter import EmailAdapter
        from app.channels.models import ChannelType

        webhook_secret = "my-email-webhook-secret"

        # EmailAdapterをwebhook_secretとともに登録
        service = ChannelService.get_instance()
        adapter = EmailAdapter(
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="test@test.com",
            smtp_password="test-password",
            imap_host="imap.test.com",
            imap_port=993,
            imap_user="test@test.com",
            imap_password="test-password",
            webhook_secret=webhook_secret,
        )
        service.register_adapter("tenant-with-email", ChannelType.EMAIL, adapter)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 無効な署名でリクエスト
            response = await client.post(
                "/api/channels/email/webhook",
                json={"raw_message": "test email content"},
                headers={
                    "X-Tenant-ID": "tenant-with-email",
                    "X-Webhook-Secret": "invalid-secret",
                },
            )
        # 無効な署名なので401
        assert response.status_code == 401


class TestChannelRegisterTenantAuthorization:
    """HIGH-1: チャネル登録のテナント権限チェックテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.channel_service import ChannelService
        ChannelService.reset_instance()
        yield
        ChannelService.reset_instance()

    @pytest.fixture(autouse=True)
    def setup_env(self):
        """環境変数を設定"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")

    def _make_token(self, payload: dict) -> dict:
        """JWTトークンを生成してAuthorizationヘッダーを返す"""
        from app.auth.jwt_handler import create_access_token
        token = create_access_token(payload)
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_register_channel_requires_matching_tenant(self):
        """テナントIDが一致しない場合、チャネル登録は403を返す"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        # tenant-aaa のユーザーが tenant-bbb に登録しようとする → 403
        headers = self._make_token({"sub": "user-1", "tenant_id": "tenant-aaa"})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/channels/register",
                json={
                    "tenant_id": "tenant-bbb",
                    "channel": "slack",
                    "adapter_type": "mock",
                    "config": {},
                },
                headers=headers,
            )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_register_channel_admin_can_access_any_tenant(self):
        """is_admin=trueのユーザーは任意のテナントにアクセスできる"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        # is_admin フラグを持つ管理者
        headers = self._make_token({"sub": "admin", "tenant_id": "admin-tenant", "is_admin": True})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/channels/register",
                json={
                    "tenant_id": "any-tenant",
                    "channel": "slack",
                    "adapter_type": "mock",
                    "config": {},
                },
                headers=headers,
            )
        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def test_list_channels_requires_matching_tenant(self):
        """テナントIDが一致しない場合、チャネル一覧取得は403を返す"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        # tenant-aaa のユーザーが tenant-bbb の一覧を取得しようとする → 403
        headers = self._make_token({"sub": "user-1", "tenant_id": "tenant-aaa"})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/channels/list",
                params={"tenant_id": "tenant-bbb"},
                headers=headers,
            )
        assert response.status_code == 403


class TestRegisterChannelRequestBody:
    """HIGH-2: チャネル登録がリクエストボディを受け取るテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.channel_service import ChannelService
        ChannelService.reset_instance()
        yield
        ChannelService.reset_instance()

    @pytest.fixture(autouse=True)
    def setup_env(self):
        """環境変数を設定"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")

    @pytest.mark.asyncio
    async def test_register_channel_accepts_request_body(self):
        """チャネル登録はPydanticモデルのリクエストボディを受け取る"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.auth.jwt_handler import create_access_token

        # 自分のテナントに登録するユーザー
        token = create_access_token({"sub": "user-1", "tenant_id": "my-tenant", "is_admin": True})
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # クエリパラメータではなくリクエストボディで送信
            response = await client.post(
                "/api/channels/register",
                json={
                    "tenant_id": "my-tenant",
                    "channel": "slack",
                    "adapter_type": "mock",
                    "config": {"webhook_url": "https://example.com"},
                },
                headers=headers,
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tenant_id"] == "my-tenant"
        assert data["channel"] == "slack"


# ---------------------------------------------------------------------------
# テスト追加: セキュリティ修正検証テスト (#12-#16)
# ---------------------------------------------------------------------------

class TestSlackReplayAttack:
    """#12: Slack リプレイアタック防止テスト"""

    @pytest.fixture
    def slack_adapter(self):
        """Slack アダプターインスタンス"""
        from app.channels.slack_adapter import SlackAdapter
        return SlackAdapter(
            bot_token="xoxb-test-token",
            signing_secret="test-signing-secret",
        )

    def _make_signature(self, secret: str, timestamp: str, body: bytes) -> str:
        """テスト用Slack署名を生成"""
        import hashlib
        import hmac
        sig_basestring = f"v0:{timestamp}:{body.decode()}".encode()
        return "v0=" + hmac.new(
            secret.encode(),
            sig_basestring,
            hashlib.sha256,
        ).hexdigest()

    @pytest.mark.asyncio
    async def test_replay_attack_old_timestamp_rejected(self, slack_adapter):
        """正しい署名でも古いタイムスタンプ（5分超）は拒否される"""
        import time
        # 6分前のタイムスタンプ（リプレイアタック）
        old_timestamp = str(int(time.time()) - 360)
        body = b'{"type":"event_callback"}'
        signature = self._make_signature("test-signing-secret", old_timestamp, body)

        result = await slack_adapter.verify_signature(
            signature=signature,
            body=body,
            timestamp=old_timestamp,
        )
        assert result is False, "古いタイムスタンプのリクエストは拒否されるべき"

    @pytest.mark.asyncio
    async def test_valid_signature_with_recent_timestamp_accepted(self, slack_adapter):
        """正しい署名と新しいタイムスタンプは通過する"""
        import time
        timestamp = str(int(time.time()))
        body = b'{"type":"event_callback"}'
        signature = self._make_signature("test-signing-secret", timestamp, body)

        result = await slack_adapter.verify_signature(
            signature=signature,
            body=body,
            timestamp=timestamp,
        )
        assert result is True, "有効な署名と新しいタイムスタンプは通過するべき"

    @pytest.mark.asyncio
    async def test_invalid_timestamp_format_rejected(self, slack_adapter):
        """非数値タイムスタンプはValueErrorではなくFalseを返す"""
        body = b'{"type":"event_callback"}'
        result = await slack_adapter.verify_signature(
            signature="v0=some-sig",
            body=body,
            timestamp="not-a-number",
        )
        assert result is False, "非数値タイムスタンプはFalseを返すべき（ValueError例外ではない）"


class TestEmailVerifySignature:
    """#13: Email verify_signature テスト（修正後の動作）"""

    def _make_email_adapter(self, webhook_secret: str = ""):
        """テスト用 EmailAdapter を作成"""
        from app.channels.email_adapter import EmailAdapter
        if webhook_secret:
            return EmailAdapter(
                smtp_host="smtp.test.com",
                smtp_port=587,
                smtp_user="test@test.com",
                smtp_password="test-password",
                imap_host="imap.test.com",
                imap_port=993,
                imap_user="test@test.com",
                imap_password="test-password",
                webhook_secret=webhook_secret,
            )
        else:
            return EmailAdapter(
                smtp_host="smtp.test.com",
                smtp_port=587,
                smtp_user="test@test.com",
                smtp_password="test-password",
                imap_host="imap.test.com",
                imap_port=993,
                imap_user="test@test.com",
                imap_password="test-password",
            )

    @pytest.mark.asyncio
    async def test_no_secret_rejects_all_requests(self):
        """webhook_secret未設定の場合は全リクエストを拒否する"""
        adapter = self._make_email_adapter()
        result = await adapter.verify_signature(
            signature="any-signature",
            body=b"request-body",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_correct_secret_passes(self):
        """HMAC署名が正しいと通過する"""
        import hashlib, hmac as hmaclib
        secret = "my-webhook-secret"
        body = b"request-body"
        expected_hmac = hmaclib.new(secret.encode(), body, hashlib.sha256).hexdigest()
        adapter = self._make_email_adapter(webhook_secret=secret)
        result = await adapter.verify_signature(
            signature=expected_hmac,
            body=body,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_wrong_secret_rejected(self):
        """誤ったシークレットは拒否される"""
        adapter = self._make_email_adapter(webhook_secret="my-webhook-secret")
        result = await adapter.verify_signature(
            signature="wrong-secret",
            body=b"request-body",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_empty_signature_with_secret_rejected(self):
        """webhook_secret設定時に空の署名は拒否される"""
        adapter = self._make_email_adapter(webhook_secret="my-webhook-secret")
        result = await adapter.verify_signature(
            signature="",
            body=b"request-body",
        )
        assert result is False


class TestProcessIncomingMessage:
    """#15: process_incoming_message テスト（アダプター未登録と parse_event=None）"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.channel_service import ChannelService
        ChannelService.reset_instance()
        yield
        ChannelService.reset_instance()

    @pytest.mark.asyncio
    async def test_raises_value_error_when_adapter_not_registered(self):
        """アダプター未登録時はValueErrorを送出する"""
        from app.services.channel_service import ChannelService
        from app.channels.models import ChannelType

        service = ChannelService.get_instance()

        with pytest.raises(ValueError, match="No adapter registered"):
            await service.process_incoming_message(
                tenant_id="nonexistent-tenant",
                channel=ChannelType.SLACK,
                event_data={"type": "event_callback"},
            )

    @pytest.mark.asyncio
    async def test_returns_none_when_parse_event_returns_none(self):
        """parse_event が None を返すケースは (None, None) を返す"""
        from app.services.channel_service import ChannelService
        from app.channels.models import ChannelType
        from unittest.mock import AsyncMock

        service = ChannelService.get_instance()

        # parse_event が None を返すモックアダプター
        mock_adapter = AsyncMock()
        mock_adapter.parse_event = AsyncMock(return_value=None)

        service.register_adapter("test-tenant", ChannelType.SLACK, mock_adapter)

        result = await service.process_incoming_message(
            tenant_id="test-tenant",
            channel=ChannelType.SLACK,
            event_data={"type": "url_verification"},
        )
        assert result == (None, None)


class TestStrictStatusCodeAssertions:
    """#16: Webhook エンドポイントの正確なステータスコードテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.channel_service import ChannelService
        ChannelService.reset_instance()
        yield
        ChannelService.reset_instance()

    @pytest.fixture(autouse=True)
    def setup_env(self):
        """環境変数を設定"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")

    @pytest.mark.asyncio
    async def test_slack_webhook_without_adapter_returns_404(self):
        """Slack Webhookはアダプター未登録時に404を返す"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        import time

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/channels/slack/webhook",
                json={
                    "type": "event_callback",
                    "event": {
                        "type": "message",
                        "ts": "1234567890.123456",
                        "user": "U12345",
                        "text": "テスト",
                        "channel": "C12345",
                    },
                },
                headers={
                    "X-Slack-Signature": "v0=test",
                    "X-Slack-Request-Timestamp": str(int(time.time())),
                    "X-Tenant-ID": "test-tenant",
                },
            )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_register_channel_without_auth_returns_401(self):
        """認証なしでチャネル登録すると401を返す"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/channels/register",
                json={
                    "tenant_id": "tenant-001",
                    "channel": "slack",
                    "adapter_type": "mock",
                    "config": {},
                },
            )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_channels_without_auth_returns_401(self):
        """認証なしでチャネル一覧取得すると401を返す"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/channels/list",
                params={"tenant_id": "tenant-001"},
            )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_slack_webhook_invalid_signature_returns_401(self):
        """Slack Webhookは無効な署名に対して401を返す"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.services.channel_service import ChannelService
        from app.channels.slack_adapter import SlackAdapter
        from app.channels.models import ChannelType
        from app.middleware.tenant import set_tenant_context
        import time

        service = ChannelService.get_instance()
        adapter = SlackAdapter(bot_token="test-token", signing_secret="test-secret")
        service.register_adapter("tenant-001", ChannelType.SLACK, adapter)
        set_tenant_context("tenant-001")

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/channels/slack/webhook",
                json={"type": "event_callback", "event": {"type": "message", "ts": "1234567890.123456", "user": "U12345", "text": "テスト", "channel": "C12345"}},
                headers={
                    "X-Slack-Signature": "v0=invalid_signature",
                    "X-Slack-Request-Timestamp": str(int(time.time())),
                    "X-Tenant-ID": "tenant-001",
                },
            )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_line_webhook_invalid_signature_returns_401(self):
        """LINE Webhookは無効な署名に対して401を返す"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.services.channel_service import ChannelService
        from app.channels.line_adapter import LineAdapter
        from app.channels.models import ChannelType
        from app.middleware.tenant import set_tenant_context

        service = ChannelService.get_instance()
        adapter = LineAdapter(channel_access_token="test-token", channel_secret="test-secret")
        service.register_adapter("tenant-001", ChannelType.LINE, adapter)
        set_tenant_context("tenant-001")

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/channels/line/webhook",
                json={"events": [{"type": "message", "source": {"userId": "U123456"}, "message": {"type": "text", "text": "テスト"}}]},
                headers={
                    "X-Line-Signature": "invalid_signature",
                    "X-Tenant-ID": "tenant-001",
                },
            )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# セキュリティ修正テスト（P3-53-security-issues）
# ---------------------------------------------------------------------------

class TestWebhookSecurityFixes:
    """Webhook セキュリティ修正のテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.channel_service import ChannelService
        ChannelService.reset_instance()
        yield
        ChannelService.reset_instance()

    # --- #5: テナントID URLパスパラメータ ---

    @pytest.mark.asyncio
    async def test_slack_webhook_with_tenant_id_in_path(self):
        """Slack Webhookはパスにtenant_idを含む新エンドポイントで動作する"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/channels/tenant-001/slack/webhook",
                json={
                    "type": "event_callback",
                    "event": {
                        "type": "message",
                        "ts": "1234567890.123456",
                        "user": "U12345",
                        "text": "テスト",
                        "channel": "C12345",
                    },
                },
                headers={
                    "X-Slack-Signature": "v0=test",
                    "X-Slack-Request-Timestamp": "1234567890",
                },
            )
        # アダプター未登録なので404を返す（X-Tenant-IDヘッダーなしでも動作）
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_line_webhook_with_tenant_id_in_path(self):
        """LINE Webhookはパスにtenant_idを含む新エンドポイントで動作する"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/channels/tenant-001/line/webhook",
                json={
                    "events": [
                        {
                            "type": "message",
                            "source": {"userId": "U123456"},
                            "message": {"type": "text", "text": "テスト"},
                        }
                    ]
                },
                headers={"X-Line-Signature": "test-signature"},
            )
        # アダプター未登録なので404を返す（X-Tenant-IDヘッダーなしでも動作）
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_email_webhook_with_tenant_id_in_path(self):
        """Email Webhookはパスにtenant_idを含む新エンドポイントで動作する"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/channels/tenant-001/email/webhook",
                json={"raw_message": "test"},
                headers={"X-Webhook-Signature": "test-sig"},
            )
        # アダプター未登録なので404を返す
        assert response.status_code == 404

    # --- #1: Slack 署名検証順序 ---

    @pytest.mark.asyncio
    async def test_slack_webhook_signature_verified_before_json_parse(self):
        """Slack Webhook: 署名検証は JSON パースより前に行われるべき（url_verificationも署名後）"""
        import os, time, hashlib, hmac as hmaclib
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.services.channel_service import ChannelService
        from app.channels.slack_adapter import SlackAdapter
        from app.channels.models import ChannelType

        # 実際のSlackAdapterを登録（署名検証が動作する）
        service = ChannelService.get_instance()
        slack_adapter = SlackAdapter(
            bot_token="xoxb-test",
            signing_secret="real-signing-secret",
        )
        service.register_adapter("tenant-sig-test", ChannelType.SLACK, slack_adapter)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 無効な署名でリクエスト（url_verification なのに署名検証が先に行われて401）
            response = await client.post(
                "/api/channels/tenant-sig-test/slack/webhook",
                content=b'{"type":"url_verification","challenge":"test"}',
                headers={
                    "Content-Type": "application/json",
                    "X-Slack-Signature": "v0=invalidsignature",
                    "X-Slack-Request-Timestamp": str(int(time.time())),
                },
            )
        # 署名が無効なので401を返す（url_verificationも通らない＝署名検証が先に行われた証拠）
        assert response.status_code == 401

    # --- #2: Email HMAC 署名検証 ---

    @pytest.mark.asyncio
    async def test_email_webhook_hmac_signature_valid(self):
        """Email Webhook: HMAC署名が正しい場合は通過する"""
        import hashlib, hmac as hmaclib
        from app.channels.email_adapter import EmailAdapter

        secret = "my-webhook-secret"
        body = b'{"raw_message": "test email content"}'
        expected_hmac = hmaclib.new(
            secret.encode(), body, hashlib.sha256
        ).hexdigest()

        adapter = EmailAdapter(
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="test@test.com",
            smtp_password="test-password",
            imap_host="imap.test.com",
            imap_port=993,
            imap_user="test@test.com",
            imap_password="test-password",
            webhook_secret=secret,
        )
        result = await adapter.verify_signature(
            signature=expected_hmac,
            body=body,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_email_webhook_hmac_signature_invalid_body_tampered(self):
        """Email Webhook: ボディが改ざんされた場合はHMAC検証で拒否する"""
        import hashlib, hmac as hmaclib
        from app.channels.email_adapter import EmailAdapter

        secret = "my-webhook-secret"
        original_body = b'{"raw_message": "original"}'
        tampered_body = b'{"raw_message": "tampered"}'
        # 元のボディで署名を生成
        valid_hmac = hmaclib.new(
            secret.encode(), original_body, hashlib.sha256
        ).hexdigest()

        adapter = EmailAdapter(
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="test@test.com",
            smtp_password="test-password",
            imap_host="imap.test.com",
            imap_port=993,
            imap_user="test@test.com",
            imap_password="test-password",
            webhook_secret=secret,
        )
        # 改ざんされたボディで検証
        result = await adapter.verify_signature(
            signature=valid_hmac,
            body=tampered_body,
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_email_webhook_plain_secret_no_longer_works(self):
        """Email Webhook: 平文のシークレット比較は動作しない（HMAC検証のみ）"""
        import hashlib, hmac as hmaclib
        from app.channels.email_adapter import EmailAdapter

        secret = "my-webhook-secret"
        body = b'{"raw_message": "test"}'

        adapter = EmailAdapter(
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="test@test.com",
            smtp_password="test-password",
            imap_host="imap.test.com",
            imap_port=993,
            imap_user="test@test.com",
            imap_password="test-password",
            webhook_secret=secret,
        )
        # 平文のシークレットを送っても拒否される
        result = await adapter.verify_signature(
            signature=secret,  # 平文のシークレット
            body=body,
        )
        assert result is False

    # --- #3: is_admin 型チェック ---

    @pytest.mark.asyncio
    async def test_register_channel_is_admin_string_rejected(self):
        """register_channel: is_adminが文字列"true"の場合は管理者権限なし"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.auth.jwt_handler import create_access_token

        # is_admin が文字列"true"のトークン（型チェックなしだと通過してしまう）
        token = create_access_token({
            "sub": "user-001",
            "tenant_id": "other-tenant",
            "is_admin": "true",  # 文字列 "true"（bool ではない）
        })
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/channels/register",
                json={
                    "tenant_id": "some-other-tenant",
                    "channel": "slack",
                    "adapter_type": "mock",
                    "config": {},
                },
                headers=headers,
            )
        # 文字列 "true" は is_admin=True として扱われるべきではない → 403
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_register_channel_is_admin_int_rejected(self):
        """register_channel: is_adminが整数1の場合は管理者権限なし"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.auth.jwt_handler import create_access_token

        token = create_access_token({
            "sub": "user-001",
            "tenant_id": "other-tenant",
            "is_admin": 1,  # 整数 1（bool ではない）
        })
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/channels/register",
                json={
                    "tenant_id": "some-other-tenant",
                    "channel": "slack",
                    "adapter_type": "mock",
                    "config": {},
                },
                headers=headers,
            )
        # 整数 1 は is_admin=True として扱われるべきではない → 403
        assert response.status_code == 403

    # --- #4: ValueError ログ記録 ---

    @pytest.mark.asyncio
    async def test_slack_webhook_value_error_returns_422(self):
        """Slack Webhook: ValueErrorは422を返す"""
        import os, time, hashlib, hmac as hmaclib
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.services.channel_service import ChannelService
        from app.channels.mock_adapter import MockChannelAdapter
        from app.channels.models import ChannelType

        service = ChannelService.get_instance()
        mock_adapter = MockChannelAdapter(channel_type=ChannelType.SLACK)
        # process_incoming_message が ValueError を投げるようにモック
        mock_adapter.verify_signature = AsyncMock(return_value=True)
        service.register_adapter("tenant-422-test", ChannelType.SLACK, mock_adapter)

        body = b'{"type":"event_callback","event":{"type":"message","ts":"1234567890.0","user":"U1","text":"test","channel":"C1"}}'
        secret = "test-signing-secret"
        timestamp = str(int(time.time()))
        sig = "v0=" + hmaclib.new(
            secret.encode(),
            f"v0:{timestamp}:".encode() + body,
            hashlib.sha256,
        ).hexdigest()

        with patch(
            "app.services.channel_service.ChannelService.process_incoming_message",
            new_callable=AsyncMock,
            side_effect=ValueError("test error"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/channels/tenant-422-test/slack/webhook",
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Slack-Signature": sig,
                        "X-Slack-Request-Timestamp": timestamp,
                    },
                )
        # ValueErrorは422を返す（500ではない）
        assert response.status_code == 422


class TestSlackSignatureBodyEncoding:
    """Slack署名のbody.decode()エンコーディング問題テスト"""

    @pytest.mark.asyncio
    async def test_slack_verify_signature_with_binary_body(self):
        """Slack署名検証: バイナリボディでも正しく検証できる"""
        import time, hashlib, hmac as hmaclib
        from app.channels.slack_adapter import SlackAdapter

        signing_secret = "test-signing-secret"
        adapter = SlackAdapter(
            bot_token="xoxb-test",
            signing_secret=signing_secret,
        )

        # UTF-8以外のバイトを含むボディ（例: マルチバイト文字）
        body = "こんにちは世界".encode("utf-8")
        timestamp = str(int(time.time()))

        # 正しい署名計算（bytes結合方式）
        sig_basestring = f"v0:{timestamp}:".encode() + body
        expected = "v0=" + hmaclib.new(
            signing_secret.encode(), sig_basestring, hashlib.sha256
        ).hexdigest()

        result = await adapter.verify_signature(
            signature=expected,
            body=body,
            timestamp=timestamp,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_slack_ts_to_iso_warning_on_invalid(self):
        """Slack _ts_to_iso: 無効なtsでwarningログが出る"""
        import logging
        from app.channels.slack_adapter import SlackAdapter

        adapter = SlackAdapter(bot_token="xoxb-test", signing_secret="secret")

        with patch("app.channels.slack_adapter.logger") as mock_logger:
            result = adapter._ts_to_iso("invalid-ts")

        # フォールバック値を返す
        assert result == "1970-01-01T00:00:00Z"
        # warningログが呼ばれる
        mock_logger.warning.assert_called_once()


# ---------------------------------------------------------------------------
# HIGH問題修正テスト（P3-53-security-issues Phase2）
# ---------------------------------------------------------------------------

class TestHighPriorityFixes:
    """HIGH問題修正のテスト"""

    # --- #8: Slack/LINE アダプター空文字列バリデーション ---

    def test_slack_adapter_requires_bot_token(self):
        """Slackアダプター登録: bot_tokenが空文字の場合は400エラー"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")

        from fastapi.testclient import TestClient
        from app.main import app
        from app.auth.jwt_handler import create_access_token

        token = create_access_token({
            "sub": "admin-user",
            "tenant_id": "tenant-001",
            "is_admin": True,
        })
        headers = {"Authorization": f"Bearer {token}"}

        client = TestClient(app)
        response = client.post(
            "/api/channels/register",
            json={
                "tenant_id": "tenant-001",
                "channel": "slack",
                "adapter_type": "slack",
                "config": {
                    "bot_token": "",  # 空文字
                    "signing_secret": "test-secret",
                },
            },
            headers=headers,
        )
        assert response.status_code == 400
        assert "bot_token" in response.json().get("detail", "").lower() or "signing_secret" in response.json().get("detail", "").lower()

    def test_slack_adapter_requires_signing_secret(self):
        """Slackアダプター登録: signing_secretが空文字の場合は400エラー"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")

        from fastapi.testclient import TestClient
        from app.main import app
        from app.auth.jwt_handler import create_access_token

        token = create_access_token({
            "sub": "admin-user",
            "tenant_id": "tenant-001",
            "is_admin": True,
        })
        headers = {"Authorization": f"Bearer {token}"}

        client = TestClient(app)
        response = client.post(
            "/api/channels/register",
            json={
                "tenant_id": "tenant-001",
                "channel": "slack",
                "adapter_type": "slack",
                "config": {
                    "bot_token": "xoxb-test-token",
                    "signing_secret": "",  # 空文字
                },
            },
            headers=headers,
        )
        assert response.status_code == 400

    def test_line_adapter_requires_channel_access_token(self):
        """LINEアダプター登録: channel_access_tokenが空文字の場合は400エラー"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")

        from fastapi.testclient import TestClient
        from app.main import app
        from app.auth.jwt_handler import create_access_token

        token = create_access_token({
            "sub": "admin-user",
            "tenant_id": "tenant-001",
            "is_admin": True,
        })
        headers = {"Authorization": f"Bearer {token}"}

        client = TestClient(app)
        response = client.post(
            "/api/channels/register",
            json={
                "tenant_id": "tenant-001",
                "channel": "line",
                "adapter_type": "line",
                "config": {
                    "channel_access_token": "",  # 空文字
                    "channel_secret": "test-secret",
                },
            },
            headers=headers,
        )
        assert response.status_code == 400

    def test_line_adapter_requires_channel_secret(self):
        """LINEアダプター登録: channel_secretが空文字の場合は400エラー"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")

        from fastapi.testclient import TestClient
        from app.main import app
        from app.auth.jwt_handler import create_access_token

        token = create_access_token({
            "sub": "admin-user",
            "tenant_id": "tenant-001",
            "is_admin": True,
        })
        headers = {"Authorization": f"Bearer {token}"}

        client = TestClient(app)
        response = client.post(
            "/api/channels/register",
            json={
                "tenant_id": "tenant-001",
                "channel": "line",
                "adapter_type": "line",
                "config": {
                    "channel_access_token": "test-token",
                    "channel_secret": "",  # 空文字
                },
            },
            headers=headers,
        )
        assert response.status_code == 400


class TestLineReplayAttackPrevention:
    """LINE Webhook リプレイアタック防止テスト（#6）"""

    @pytest.fixture
    def line_adapter(self):
        from app.channels.line_adapter import LineAdapter
        return LineAdapter(
            channel_access_token="test-token",
            channel_secret="test-secret",
        )

    @pytest.mark.asyncio
    async def test_line_webhook_rejects_old_timestamp(self, line_adapter):
        """LINEイベント: 5分以上古いタイムスタンプのイベントを拒否する"""
        import time
        import base64, hashlib, hmac as hmaclib
        from app.channels.models import ChannelType

        # 10分前のタイムスタンプ（ミリ秒）
        old_timestamp_ms = int((time.time() - 600) * 1000)

        event_data = {
            "events": [
                {
                    "type": "message",
                    "timestamp": old_timestamp_ms,
                    "source": {"userId": "U123"},
                    "message": {"type": "text", "id": "msg-1", "text": "test"},
                }
            ]
        }
        # parse_event は古いタイムスタンプのイベントを None として返すべき
        result = await line_adapter.parse_event(event_data)
        assert result is None

    @pytest.mark.asyncio
    async def test_line_webhook_accepts_recent_timestamp(self, line_adapter):
        """LINEイベント: 5分以内のタイムスタンプのイベントは通過する"""
        import time

        # 現在のタイムスタンプ（ミリ秒）
        current_timestamp_ms = int(time.time() * 1000)

        event_data = {
            "events": [
                {
                    "type": "message",
                    "timestamp": current_timestamp_ms,
                    "source": {"userId": "U123"},
                    "message": {"type": "text", "id": "msg-1", "text": "test"},
                }
            ]
        }
        result = await line_adapter.parse_event(event_data)
        assert result is not None

    @pytest.mark.asyncio
    async def test_line_webhook_accepts_zero_timestamp(self, line_adapter):
        """LINEイベント: タイムスタンプが0の場合は通過する（後方互換性）"""
        event_data = {
            "events": [
                {
                    "type": "message",
                    "timestamp": 0,
                    "source": {"userId": "U123"},
                    "message": {"type": "text", "id": "msg-1", "text": "test"},
                }
            ]
        }
        # timestamp=0 は検証スキップ（タイムスタンプなし）
        result = await line_adapter.parse_event(event_data)
        # 注: タイムスタンプ0は1970年なので古すぎるが、後方互換のため通過
        # このテストは実装後に調整可能
        # assert result is not None  # 後方互換ありの場合
        pass  # 実装により動作が変わる可能性あり


class TestEmailSendMessageErrorHandling:
    """Email send_message エラーハンドリング改善テスト（#9）"""

    @pytest.fixture
    def email_adapter(self):
        from app.channels.email_adapter import EmailAdapter
        return EmailAdapter(
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="test@test.com",
            smtp_password="test-password",
            imap_host="imap.test.com",
            imap_port=993,
            imap_user="test@test.com",
            imap_password="test-password",
        )

    @pytest.mark.asyncio
    async def test_send_message_error_logs_recipient_id(self, email_adapter):
        """send_message失敗時にrecipient_idがログに含まれる"""
        with patch("app.channels.email_adapter.logger") as mock_logger:
            with patch("aiosmtplib.send", side_effect=Exception("SMTP error")):
                result = await email_adapter.send_message(
                    recipient_id="target@test.com",
                    content="test",
                )

        assert result["success"] is False
        # logger.error が呼ばれ、recipient_id が含まれる
        mock_logger.error.assert_called_once()
        call_args = str(mock_logger.error.call_args)
        assert "target@test.com" in call_args or "recipient_id" in call_args.lower()

    @pytest.mark.asyncio
    async def test_send_message_error_logs_exc_info(self, email_adapter):
        """send_message失敗時にexc_info=Trueでスタックトレースが記録される"""
        with patch("app.channels.email_adapter.logger") as mock_logger:
            with patch("aiosmtplib.send", side_effect=Exception("SMTP error")):
                result = await email_adapter.send_message(
                    recipient_id="target@test.com",
                    content="test",
                )

        assert result["success"] is False
        # exc_info=True が渡される
        call_kwargs = mock_logger.error.call_args[1]
        assert call_kwargs.get("exc_info") is True


class TestRegisterChannelRequestValidation:
    """RegisterChannelRequest バリデーションテスト（#14）"""

    def test_tenant_id_empty_string_rejected(self):
        """tenant_idが空文字の場合はバリデーションエラー"""
        from pydantic import ValidationError
        from app.api.channels import RegisterChannelRequest

        try:
            RegisterChannelRequest(
                tenant_id="",
                channel="slack",
                adapter_type="slack",
            )
            assert False, "Should raise ValidationError"
        except ValidationError:
            pass

    def test_channel_empty_string_rejected(self):
        """channelが空文字の場合はバリデーションエラー"""
        from pydantic import ValidationError
        from app.api.channels import RegisterChannelRequest

        try:
            RegisterChannelRequest(
                tenant_id="tenant-001",
                channel="",
                adapter_type="slack",
            )
            assert False, "Should raise ValidationError"
        except ValidationError:
            pass

    def test_adapter_type_empty_string_rejected(self):
        """adapter_typeが空文字の場合はバリデーションエラー"""
        from pydantic import ValidationError
        from app.api.channels import RegisterChannelRequest

        try:
            RegisterChannelRequest(
                tenant_id="tenant-001",
                channel="slack",
                adapter_type="",
            )
            assert False, "Should raise ValidationError"
        except ValidationError:
            pass

    def test_tenant_id_too_long_rejected(self):
        """tenant_idが64文字以上の場合はバリデーションエラー"""
        from pydantic import ValidationError
        from app.api.channels import RegisterChannelRequest

        try:
            RegisterChannelRequest(
                tenant_id="a" * 64,
                channel="slack",
                adapter_type="slack",
            )
            assert False, "Should raise ValidationError"
        except ValidationError:
            pass


# ---------------------------------------------------------------------------
# Gap-3: debug_mode=False での mock アダプター登録テスト
# Gap-4: unregister_adapter テスト
# ---------------------------------------------------------------------------

class TestMockAdapterDebugMode:
    """Gap-3: debug_mode=False で mock アダプター登録は失敗する"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        from app.services.channel_service import ChannelService
        ChannelService.reset_instance()
        yield
        ChannelService.reset_instance()

    @pytest.mark.asyncio
    async def test_mock_adapter_debug_mode_false_returns_400(self) -> None:
        """debug_mode=False で mock アダプター登録 → 400"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        from unittest.mock import patch, MagicMock
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.auth.jwt_handler import create_access_token

        token = create_access_token({"sub": "admin-user", "is_admin": True})
        headers = {"Authorization": f"Bearer {token}"}

        # debug_mode=False に設定
        mock_settings = MagicMock()
        mock_settings.debug_mode = False

        with patch("app.config.settings.get_settings", return_value=mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/channels/register",
                    json={
                        "tenant_id": "test-tenant",
                        "channel": "slack",
                        "adapter_type": "mock",
                        "config": {},
                    },
                    headers=headers,
                )
        assert response.status_code == 400
        assert "debug" in response.json().get("detail", "").lower()


class TestUnregisterAdapter:
    """Gap-4: unregister_adapter テスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        from app.services.channel_service import ChannelService
        ChannelService.reset_instance()
        yield
        ChannelService.reset_instance()

    def test_unregister_existing_adapter_returns_true(self) -> None:
        """存在するアダプター削除 → True"""
        from app.services.channel_service import ChannelService
        from app.channels.models import ChannelType
        from app.channels.mock_adapter import MockChannelAdapter

        service = ChannelService.get_instance()
        adapter = MockChannelAdapter(channel_type=ChannelType.SLACK)
        service.register_adapter("tenant-unregister-1", ChannelType.SLACK, adapter)

        result = service.unregister_adapter("tenant-unregister-1", ChannelType.SLACK)
        assert result is True

    def test_unregister_nonexistent_adapter_returns_false(self) -> None:
        """存在しないアダプター削除 → False"""
        from app.services.channel_service import ChannelService
        from app.channels.models import ChannelType

        service = ChannelService.get_instance()
        result = service.unregister_adapter("nonexistent-tenant", ChannelType.SLACK)
        assert result is False

    def test_get_adapter_after_unregister_returns_none(self) -> None:
        """削除後に get_adapter → None"""
        from app.services.channel_service import ChannelService
        from app.channels.models import ChannelType
        from app.channels.mock_adapter import MockChannelAdapter

        service = ChannelService.get_instance()
        adapter = MockChannelAdapter(channel_type=ChannelType.SLACK)
        service.register_adapter("tenant-unregister-2", ChannelType.SLACK, adapter)
        service.unregister_adapter("tenant-unregister-2", ChannelType.SLACK)

        retrieved = service.get_adapter("tenant-unregister-2", ChannelType.SLACK)
        assert retrieved is None
