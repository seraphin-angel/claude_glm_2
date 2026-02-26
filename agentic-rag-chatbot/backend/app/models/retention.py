"""P3-49: データ保持ポリシー（GDPR）- モデル定義"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, field_validator


class RetentionPolicy(BaseModel):
    """データ保持ポリシーモデル"""

    model_config = {"frozen": True}

    tenant_id: str
    data_type: str
    retention_days: int
    is_active: bool = True
    created_at: datetime = None

    def model_post_init(self, __context) -> None:
        """初期化後処理: created_atのデフォルト設定"""
        # frozen=TrueなのでPydanticの初期化後に設定
        object.__setattr__(
            self,
            "created_at",
            self.created_at or datetime.now(timezone.utc),
        )

    @field_validator("retention_days")
    @classmethod
    def validate_retention_days(cls, v: int) -> int:
        """保持期間のバリデーション: 1日以上"""
        if v <= 0:
            raise ValueError("retention_days must be greater than 0")
        return v

    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id(cls, v: str) -> str:
        """テナントIDのバリデーション"""
        if not v or not v.strip():
            raise ValueError("tenant_id must not be empty")
        return v

    @field_validator("data_type")
    @classmethod
    def validate_data_type(cls, v: str) -> str:
        """データ種別のバリデーション"""
        if not v or not v.strip():
            raise ValueError("data_type must not be empty")
        return v


class DataDeletionRequest(BaseModel):
    """GDPRデータ削除リクエスト（Article 17 - Right to erasure）"""

    tenant_id: str
    user_id: str
    reason: str
    requested_at: datetime = None

    def model_post_init(self, __context) -> None:
        """初期化後処理"""
        if self.requested_at is None:
            object.__setattr__(
                self,
                "requested_at",
                datetime.now(timezone.utc),
            )

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """ユーザーIDのバリデーション"""
        if not v or not v.strip():
            raise ValueError("user_id must not be empty")
        return v

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        """削除理由のバリデーション"""
        if not v or not v.strip():
            raise ValueError("reason must not be empty")
        return v


class AuditLogEntry(BaseModel):
    """監査ログエントリ"""

    model_config = {"frozen": True}

    operation: str
    tenant_id: str
    data_type: str
    record_count: int
    performed_by: str
    timestamp: datetime = None
    details: Optional[dict] = None

    def model_post_init(self, __context) -> None:
        """初期化後処理"""
        object.__setattr__(
            self,
            "timestamp",
            self.timestamp or datetime.now(timezone.utc),
        )


class RetentionPolicyCreateRequest(BaseModel):
    """保持ポリシー作成リクエスト"""

    tenant_id: str
    data_type: str
    retention_days: int

    @field_validator("retention_days")
    @classmethod
    def validate_retention_days(cls, v: int) -> int:
        """保持期間のバリデーション"""
        if v <= 0:
            raise ValueError("retention_days must be greater than 0")
        return v
