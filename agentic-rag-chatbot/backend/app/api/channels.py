"""P3-53: マルチチャネル対応 - Webhook API エンドポイント"""

import json
import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from typing import Any

from app.channels.models import ChannelType
from app.services.channel_service import ChannelService
from app.auth.jwt_handler import verify_token
from app.rate_limit import limiter

router = APIRouter(prefix="/channels", tags=["channels"])
logger = logging.getLogger(__name__)


class RegisterChannelRequest(BaseModel):
    """チャネルアダプター登録リクエスト"""

    tenant_id: str = Field(..., min_length=1, max_length=63)
    channel: str = Field(..., min_length=1, max_length=63)
    adapter_type: str = Field(..., min_length=1, max_length=63)
    config: dict[str, str | int] = Field(default_factory=dict)


@router.post("/{tenant_id}/slack/webhook")
@limiter.limit("60/minute")
async def slack_webhook(tenant_id: str, request: Request) -> dict[str, Any]:
    """Slack Webhook エンドポイント。

    Slack Event API からのイベントを受信する。
    テナントIDはURLパスから取得する（Slackは X-Tenant-ID ヘッダーを送らない）。
    """
    # ヘッダーから署名情報を取得
    signature = request.headers.get("X-Slack-Signature", "")
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")

    # リクエストボディを取得
    body = await request.body()

    # アダプター取得（署名検証のために先に行う）
    service = ChannelService.get_instance()
    adapter = service.get_adapter(tenant_id, ChannelType.SLACK)

    if adapter is None:
        raise HTTPException(
            status_code=404,
            detail="Channel not configured for this tenant",
        )

    # 署名検証（JSONパースより前に行う）
    is_valid = await adapter.verify_signature(
        signature=signature,
        body=body,
        timestamp=timestamp,
    )
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid Slack signature")

    # JSONパース（署名検証後）
    try:
        event_data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # URL検証チャレンジ（Slack初回設定時） - 署名検証後に処理
    if event_data.get("type") == "url_verification":
        return {"challenge": event_data.get("challenge", "")}

    # メッセージ処理
    try:
        message, internal_thread_id = await service.process_incoming_message(
            tenant_id=tenant_id,
            channel=ChannelType.SLACK,
            event_data=event_data,
        )
    except ValueError as e:
        logger.error(
            "slack_webhook process_incoming_message failed: %s",
            str(e),
            extra={"tenant_id": tenant_id},
        )
        raise HTTPException(status_code=422, detail="Channel adapter error")

    if message is None:
        return {"status": "ignored"}

    # NOTE: 自動応答生成は未実装です（制限事項としてREADMEに記載済み）

    return {
        "status": "processed",
        "channel_thread_id": message.channel_thread_id,
        "internal_thread_id": str(internal_thread_id) if internal_thread_id else None,
    }


# 後方互換性のための旧エンドポイント（X-Tenant-IDヘッダー対応）
@router.post("/slack/webhook")
@limiter.limit("60/minute")
async def slack_webhook_legacy(request: Request) -> dict[str, Any]:
    """Slack Webhook エンドポイント（後方互換性: X-Tenant-IDヘッダー使用）。"""
    from app.middleware.tenant import get_current_tenant_id

    # ヘッダーから署名情報を取得
    signature = request.headers.get("X-Slack-Signature", "")
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")

    # リクエストボディを取得
    body = await request.body()

    # テナントIDをヘッダーから取得（署名検証前に必要）
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required")

    # アダプター取得（署名検証のために先に行う）
    service = ChannelService.get_instance()
    adapter = service.get_adapter(tenant_id, ChannelType.SLACK)

    if adapter is None:
        raise HTTPException(
            status_code=404,
            detail="Channel not configured for this tenant",
        )

    # 署名検証（JSONパースより前に行う）
    is_valid = await adapter.verify_signature(
        signature=signature,
        body=body,
        timestamp=timestamp,
    )
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid Slack signature")

    # JSONパース（署名検証後）
    try:
        event_data_check = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # URL検証チャレンジ（Slack初回設定時） - 署名検証後に処理
    if event_data_check.get("type") == "url_verification":
        return {"challenge": event_data_check.get("challenge", "")}

    # メッセージ処理
    try:
        message, internal_thread_id = await service.process_incoming_message(
            tenant_id=tenant_id,
            channel=ChannelType.SLACK,
            event_data=event_data_check,
        )
    except ValueError as e:
        logger.error(
            "slack_webhook process_incoming_message failed: %s",
            str(e),
            extra={"tenant_id": tenant_id},
        )
        raise HTTPException(status_code=422, detail="Channel adapter error")

    if message is None:
        return {"status": "ignored"}

    return {
        "status": "processed",
        "channel_thread_id": message.channel_thread_id,
        "internal_thread_id": str(internal_thread_id) if internal_thread_id else None,
    }


@router.post("/{tenant_id}/line/webhook")
@limiter.limit("60/minute")
async def line_webhook(tenant_id: str, request: Request) -> dict[str, Any]:
    """LINE Webhook エンドポイント。

    LINE Messaging API からの Webhook を受信する。
    テナントIDはURLパスから取得する（LINEは X-Tenant-ID ヘッダーを送らない）。
    """
    # ヘッダーから署名情報を取得
    signature = request.headers.get("X-Line-Signature", "")

    # リクエストボディを取得
    body = await request.body()

    # アダプター取得（署名検証のために先に行う）
    service = ChannelService.get_instance()
    adapter = service.get_adapter(tenant_id, ChannelType.LINE)

    if adapter is None:
        raise HTTPException(
            status_code=404,
            detail="Channel not configured for this tenant",
        )

    # 署名検証（JSONパースより前に行う）
    is_valid = await adapter.verify_signature(
        signature=signature,
        body=body,
    )
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid LINE signature")

    # JSONパース（署名検証後）
    try:
        event_data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # メッセージ処理
    try:
        message, internal_thread_id = await service.process_incoming_message(
            tenant_id=tenant_id,
            channel=ChannelType.LINE,
            event_data=event_data,
        )
    except ValueError as e:
        logger.error(
            "line_webhook process_incoming_message failed: %s",
            str(e),
            extra={"tenant_id": tenant_id},
        )
        raise HTTPException(status_code=422, detail="Channel adapter error")

    if message is None:
        return {"status": "ignored"}

    # NOTE: 自動応答生成は未実装です（制限事項としてREADMEに記載済み）

    return {
        "status": "processed",
        "channel_thread_id": message.channel_thread_id,
        "internal_thread_id": str(internal_thread_id) if internal_thread_id else None,
    }


# 後方互換性のための旧エンドポイント
@router.post("/line/webhook")
@limiter.limit("60/minute")
async def line_webhook_legacy(request: Request) -> dict[str, Any]:
    """LINE Webhook エンドポイント（後方互換性: X-Tenant-IDヘッダー使用）。"""
    from app.middleware.tenant import get_current_tenant_id

    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()

    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required")

    service = ChannelService.get_instance()
    adapter = service.get_adapter(tenant_id, ChannelType.LINE)

    if adapter is None:
        raise HTTPException(
            status_code=404,
            detail="Channel not configured for this tenant",
        )

    is_valid = await adapter.verify_signature(
        signature=signature,
        body=body,
    )
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid LINE signature")

    try:
        event_data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    try:
        message, internal_thread_id = await service.process_incoming_message(
            tenant_id=tenant_id,
            channel=ChannelType.LINE,
            event_data=event_data,
        )
    except ValueError as e:
        logger.error(
            "line_webhook process_incoming_message failed: %s",
            str(e),
            extra={"tenant_id": tenant_id},
        )
        raise HTTPException(status_code=422, detail="Channel adapter error")

    if message is None:
        return {"status": "ignored"}

    return {
        "status": "processed",
        "channel_thread_id": message.channel_thread_id,
        "internal_thread_id": str(internal_thread_id) if internal_thread_id else None,
    }


@router.post("/{tenant_id}/email/webhook")
@limiter.limit("60/minute")
async def email_webhook(tenant_id: str, request: Request) -> dict[str, Any]:
    """Email Webhook エンドポイント。

    メール受信（IMAPポーリングまたは外部転送）を処理する。
    テナントIDはURLパスから取得する。
    """
    # ヘッダーから署名情報を取得
    signature = request.headers.get("X-Webhook-Signature", "")

    # リクエストボディを取得
    body = await request.body()

    # アダプター取得と署名検証
    service = ChannelService.get_instance()
    adapter = service.get_adapter(tenant_id, ChannelType.EMAIL)

    if adapter is None:
        raise HTTPException(
            status_code=404,
            detail="Channel not configured for this tenant",
        )

    # 署名検証（JSONパースより前に行う）
    is_valid = await adapter.verify_signature(
        signature=signature,
        body=body,
    )
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid Email webhook signature")

    # JSONパース（署名検証後）
    try:
        event_data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # メッセージ処理
    try:
        message, internal_thread_id = await service.process_incoming_message(
            tenant_id=tenant_id,
            channel=ChannelType.EMAIL,
            event_data=event_data,
        )
    except ValueError as e:
        logger.error(
            "email_webhook process_incoming_message failed: %s",
            str(e),
            extra={"tenant_id": tenant_id},
        )
        raise HTTPException(status_code=422, detail="Channel adapter error")

    if message is None:
        return {"status": "ignored"}

    # NOTE: 自動応答生成は未実装です（制限事項としてREADMEに記載済み）

    return {
        "status": "processed",
        "channel_thread_id": message.channel_thread_id,
        "internal_thread_id": str(internal_thread_id) if internal_thread_id else None,
    }


# 後方互換性のための旧エンドポイント
@router.post("/email/webhook")
@limiter.limit("60/minute")
async def email_webhook_legacy(request: Request) -> dict[str, Any]:
    """Email Webhook エンドポイント（後方互換性: X-Tenant-IDヘッダー使用）。"""
    from app.middleware.tenant import get_current_tenant_id

    signature = request.headers.get("X-Webhook-Signature", "")
    body = await request.body()

    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required")

    service = ChannelService.get_instance()
    adapter = service.get_adapter(tenant_id, ChannelType.EMAIL)

    if adapter is None:
        raise HTTPException(
            status_code=404,
            detail="Channel not configured for this tenant",
        )

    is_valid = await adapter.verify_signature(
        signature=signature,
        body=body,
    )
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid Email webhook signature")

    try:
        event_data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    try:
        message, internal_thread_id = await service.process_incoming_message(
            tenant_id=tenant_id,
            channel=ChannelType.EMAIL,
            event_data=event_data,
        )
    except ValueError as e:
        logger.error(
            "email_webhook process_incoming_message failed: %s",
            str(e),
            extra={"tenant_id": tenant_id},
        )
        raise HTTPException(status_code=422, detail="Channel adapter error")

    if message is None:
        return {"status": "ignored"}

    return {
        "status": "processed",
        "channel_thread_id": message.channel_thread_id,
        "internal_thread_id": str(internal_thread_id) if internal_thread_id else None,
    }


@router.post("/register")
async def register_channel_adapter(
    body: RegisterChannelRequest,
    token: dict = Depends(verify_token),
) -> dict[str, Any]:
    """チャネルアダプターを登録する（管理用）。

    Args:
        body: リクエストボディ（tenant_id, channel, adapter_type, config）
        token: JWT認証トークン

    Returns:
        登録結果

    Raises:
        HTTPException 403: テナントIDが一致しない場合（管理者を除く）
    """
    # テナント権限チェック: is_admin でない場合は自テナントのみ
    # 型チェックを厳密に行う: bool型のTrueのみ管理者として認める
    is_admin = token.get("is_admin")
    is_admin_bool = isinstance(is_admin, bool) and is_admin
    token_tenant_id = token.get("tenant_id")
    if not is_admin_bool and token_tenant_id != body.tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: cannot register channels for other tenants",
        )

    try:
        channel_type = ChannelType(body.channel)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid channel type: {body.channel}",
        )

    service = ChannelService.get_instance()
    config = body.config

    # アダプターを作成
    if body.adapter_type == "mock":
        from app.config.settings import get_settings
        settings = get_settings()
        if not settings.debug_mode:
            raise HTTPException(
                status_code=400,
                detail="Mock adapter is only allowed in debug mode",
            )
        from app.channels.mock_adapter import MockChannelAdapter
        adapter = MockChannelAdapter(channel_type=channel_type)
    elif body.adapter_type == "slack":
        from app.channels.slack_adapter import SlackAdapter
        bot_token = config.get("bot_token", "")
        signing_secret = config.get("signing_secret", "")
        if not bot_token or not signing_secret:
            raise HTTPException(
                status_code=400,
                detail="bot_token and signing_secret are required for Slack adapter",
            )
        adapter = SlackAdapter(
            bot_token=bot_token,
            signing_secret=signing_secret,
        )
    elif body.adapter_type == "line":
        from app.channels.line_adapter import LineAdapter
        channel_access_token = config.get("channel_access_token", "")
        channel_secret = config.get("channel_secret", "")
        if not channel_access_token or not channel_secret:
            raise HTTPException(
                status_code=400,
                detail="channel_access_token and channel_secret are required for LINE adapter",
            )
        adapter = LineAdapter(
            channel_access_token=channel_access_token,
            channel_secret=channel_secret,
        )
    elif body.adapter_type == "email":
        from app.channels.email_adapter import EmailAdapter
        try:
            adapter = EmailAdapter(
                smtp_host=config.get("smtp_host", ""),
                smtp_port=config.get("smtp_port", 587),
                smtp_user=config.get("smtp_user", ""),
                smtp_password=config.get("smtp_password", ""),
                imap_host=config.get("imap_host", ""),
                imap_port=config.get("imap_port", 993),
                imap_user=config.get("imap_user", ""),
                imap_password=config.get("imap_password", ""),
                webhook_secret=config.get("webhook_secret", ""),
            )
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail="Invalid email adapter configuration",
            )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown adapter type: {body.adapter_type}",
        )

    service.register_adapter(body.tenant_id, channel_type, adapter)
    logger.info(
        "channel_adapter_registered",
        extra={
            "tenant_id": body.tenant_id,
            "channel": channel_type.value,
            "adapter_type": body.adapter_type,
        },
    )

    return {
        "success": True,
        "tenant_id": body.tenant_id,
        "channel": body.channel,
        "adapter_type": body.adapter_type,
    }


@router.get("/list")
async def list_channels(
    tenant_id: str,
    token: dict = Depends(verify_token),
) -> dict[str, Any]:
    """テナントに登録されているチャネル一覧を取得する。

    Args:
        tenant_id: テナントID
        token: JWT認証トークン

    Returns:
        チャネル一覧

    Raises:
        HTTPException 403: テナントIDが一致しない場合（管理者を除く）
    """
    # テナント権限チェック: is_admin でない場合は自テナントのみ
    # 型チェックを厳密に行う: bool型のTrueのみ管理者として認める
    is_admin = token.get("is_admin")
    is_admin_bool = isinstance(is_admin, bool) and is_admin
    token_tenant_id = token.get("tenant_id")
    if not is_admin_bool and token_tenant_id != tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: cannot list channels for other tenants",
        )

    service = ChannelService.get_instance()
    channels = service.list_registered_channels(tenant_id)

    return {
        "success": True,
        "tenant_id": tenant_id,
        "channels": [c.value for c in channels],
    }
