"""P3-53: マルチチャネル対応 - Email アダプター"""

import email
import email.utils
import hashlib
import hmac
import logging
import time
import uuid
from email.message import EmailMessage as PyEmailMessage
from typing import Any, Optional

from app.channels.base import BaseChannelAdapter
from app.channels.models import ChannelMessage, ChannelType

# モジュールレベルでaiosmtplibをインポート（実行時エラーを早期検出）
try:
    import aiosmtplib
    AIOSMTPLIB_AVAILABLE = True
except ImportError:
    aiosmtplib = None  # type: ignore
    AIOSMTPLIB_AVAILABLE = False

logger = logging.getLogger(__name__)


class EmailAdapter(BaseChannelAdapter):
    """Email アダプター（SMTP/IMAP）。"""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        imap_host: str,
        imap_port: int,
        imap_user: str,
        imap_password: str,
        from_address: Optional[str] = None,
        webhook_secret: str = "",
    ):
        """Email アダプターを初期化する。

        Args:
            smtp_host: SMTP サーバーホスト
            smtp_port: SMTP サーバーポート
            smtp_user: SMTP ユーザー名
            smtp_password: SMTP パスワード
            imap_host: IMAP サーバーホスト
            imap_port: IMAP サーバーポート
            imap_user: IMAP ユーザー名
            imap_password: IMAP パスワード
            from_address: 送信元メールアドレス
            webhook_secret: Webhook 署名検証用シークレット（空文字列の場合は検証スキップ）
        """
        if not smtp_host:
            raise ValueError("smtp_host must not be empty")
        if not smtp_user:
            raise ValueError("smtp_user must not be empty")
        if not smtp_password:
            raise ValueError("smtp_password must not be empty")
        if not imap_host:
            raise ValueError("imap_host must not be empty")
        if not imap_user:
            raise ValueError("imap_user must not be empty")
        if not imap_password:
            raise ValueError("imap_password must not be empty")
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._smtp_user = smtp_user
        self._smtp_password = smtp_password
        self._imap_host = imap_host
        self._imap_port = imap_port
        self._imap_user = imap_user
        self._imap_password = imap_password
        self._from_address = from_address or smtp_user
        self._webhook_secret = webhook_secret

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.EMAIL

    async def send_message(
        self,
        recipient_id: str,
        content: str,
        thread_id: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """メールを送信する。

        Args:
            recipient_id: 送信先メールアドレス
            content: メール本文
            thread_id: 返信元の Message-ID（スレッド継続）
            **kwargs: subject（件名）などを含む追加オプション

        Returns:
            送信結果
        """
        subject = kwargs.get("subject", "Re: お問い合わせ")
        message_id = f"<{uuid.uuid4()}@{self._smtp_host}>"

        msg = PyEmailMessage()
        msg["From"] = self._from_address
        msg["To"] = recipient_id
        msg["Subject"] = subject
        msg["Message-ID"] = message_id

        # スレッド継続の場合は In-Reply-To と References を設定
        if thread_id:
            msg["In-Reply-To"] = thread_id
            msg["References"] = thread_id

        msg.set_content(content)

        try:
            if not AIOSMTPLIB_AVAILABLE or aiosmtplib is None:
                return {
                    "success": False,
                    "error": "aiosmtplib is not installed",
                }

            await aiosmtplib.send(
                msg,
                hostname=self._smtp_host,
                port=self._smtp_port,
                username=self._smtp_user,
                password=self._smtp_password,
                start_tls=True,
            )

            return {
                "success": True,
                "message_id": message_id,
                "thread_id": thread_id or message_id,
            }
        except Exception as e:
            logger.error(
                "Email send_message failed: %s recipient_id=%s",
                type(e).__name__,
                recipient_id,
                exc_info=True,
            )
            return {
                "success": False,
                "error": "メール送信に失敗しました",
            }

    async def parse_event(
        self,
        event_data: dict[str, Any],
    ) -> Optional[ChannelMessage]:
        """メールを解析する。

        Args:
            event_data: raw_message キーに EmailMessage オブジェクトを含む辞書

        Returns:
            ChannelMessage または None
        """
        raw_message = event_data.get("raw_message")
        if not raw_message:
            return None

        try:
            # EmailMessage オブジェクトまたは生のメールデータ
            if isinstance(raw_message, str):
                msg = email.message_from_string(raw_message)
            else:
                msg = raw_message

            # 本文を取得
            if msg.is_multipart():
                content = ""
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload and isinstance(payload, bytes):
                            content = payload.decode("utf-8", errors="ignore")
                        break
            else:
                payload = msg.get_payload(decode=True)
                if payload and isinstance(payload, bytes):
                    content = payload.decode("utf-8", errors="ignore")
                else:
                    content = str(msg.get_payload() or "")

            # 送信者を解析
            from_header = msg.get("From", "")
            sender_name, sender_email = email.utils.parseaddr(from_header)

            # タイムスタンプを解析
            date_header = msg.get("Date", "")
            timestamp = self._parse_date(date_header)

            return ChannelMessage(
                channel=ChannelType.EMAIL,
                channel_message_id=msg.get("Message-ID", f"<{uuid.uuid4()}>"),
                channel_thread_id=msg.get("In-Reply-To") or msg.get("References"),
                sender_id=sender_email,
                sender_name=sender_name or None,
                content=content.strip(),
                timestamp=timestamp,
                metadata={
                    "subject": msg.get("Subject", ""),
                    "to": msg.get("To", ""),
                    "cc": msg.get("Cc", ""),
                },
            )
        except Exception as e:
            logger.error(
                "parse_event failed to parse email message: %s",
                str(e),
                exc_info=True,
            )
            return None

    async def verify_signature(
        self,
        signature: str,
        body: bytes,
        timestamp: Optional[str] = None,
    ) -> bool:
        """Webhook HMAC署名検証。

        ボディのHMAC-SHA256署名を計算し、X-Webhook-Signatureヘッダーと比較する。
        これによりボディの改ざんを検知できる。

        Args:
            signature: X-Webhook-Signature ヘッダーの値（HMAC-SHA256のhexdigest）
            body: リクエストボディ（HMAC計算対象）
            timestamp: タイムスタンプ（未使用）

        Returns:
            HMAC署名が一致する場合は True、不一致または未設定の場合は False
        """
        if not self._webhook_secret:
            # シークレット未設定の場合は拒否（セキュリティ強化）
            logger.warning(
                "Email webhook_secret is not configured; rejecting all webhook requests"
            )
            return False
        expected_hmac = hmac.new(
            self._webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature, expected_hmac)

    async def health_check(self) -> bool:
        """SMTP サーバーへの接続を確認する。"""
        try:
            if not AIOSMTPLIB_AVAILABLE or aiosmtplib is None:
                logger.warning("aiosmtplib is not installed, health check skipped")
                return False

            client = aiosmtplib.SMTP(
                hostname=self._smtp_host,
                port=self._smtp_port,
            )
            await client.connect()
            await client.noop()
            await client.quit()
            return True
        except Exception as e:
            logger.error("Email health check failed: %s", str(e))
            return False

    @staticmethod
    def _parse_date(date_str: str) -> str:
        """メールの日付ヘッダーを ISO 8601 形式に変換する。"""
        try:
            parsed = email.utils.parsedate_to_datetime(date_str)
            return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")
        except (TypeError, ValueError):
            return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
