"""P3-48: マルチテナント対応 - テナントモデル定義"""

import re
from typing import Optional

from pydantic import BaseModel, field_validator


class TenantConfig(BaseModel):
    """テナントごとの設定"""

    model_config = {"frozen": True}

    llm_model: Optional[str] = None
    max_tokens: Optional[int] = None
    system_prompt_override: Optional[str] = None
    rate_limit_chat: Optional[str] = None
    rate_limit_stream: Optional[str] = None


class Tenant(BaseModel):
    """テナントモデル"""

    model_config = {"frozen": True}

    tenant_id: str
    name: str
    config: TenantConfig = TenantConfig()
    is_active: bool = True

    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id(cls, v: str) -> str:
        """テナントIDのバリデーション: 英数字とハイフンのみ、空不可"""
        if not v:
            raise ValueError("tenant_id must not be empty")
        if not re.match(r"^[a-z0-9][a-z0-9\-]{0,62}$", v):
            raise ValueError(
                "tenant_id must start with alphanumeric and contain only "
                "lowercase alphanumeric characters and hyphens (max 63 chars)"
            )
        return v


class TenantCreateRequest(BaseModel):
    """テナント作成リクエスト"""

    tenant_id: str
    name: str
    config: TenantConfig = TenantConfig()

    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id(cls, v: str) -> str:
        """テナントIDのバリデーション"""
        if not v:
            raise ValueError("tenant_id must not be empty")
        if not re.match(r"^[a-z0-9][a-z0-9\-]{0,62}$", v):
            raise ValueError(
                "tenant_id must start with alphanumeric and contain only "
                "lowercase alphanumeric characters and hyphens (max 63 chars)"
            )
        return v


class TenantUpdateConfigRequest(BaseModel):
    """テナント設定更新リクエスト"""

    config: TenantConfig


class TenantResponse(BaseModel):
    """テナントレスポンス"""

    tenant_id: str
    name: str
    config: TenantConfig
    is_active: bool
