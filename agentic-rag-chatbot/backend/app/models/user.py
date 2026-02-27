"""P3-54: パーソナライゼーション - ユーザーモデル定義"""

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator


class UserPlan(str, Enum):
    """ユーザープラン"""
    
    FREE = "free"
    PAID = "paid"


class ConversationRecord(BaseModel):
    """会話履歴レコード"""
    
    model_config = {"frozen": True}
    
    question: str
    category: Optional[str] = None
    timestamp: datetime | None = None
    feedback_score: Optional[int] = None
    
    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        """質問は空にできない"""
        if not v or not v.strip():
            raise ValueError("question must not be empty")
        return v
    
    @field_validator("feedback_score")
    @classmethod
    def validate_feedback_score(cls, v: Optional[int]) -> Optional[int]:
        """フィードバックスコアは1-5の範囲"""
        if v is not None and (v < 1 or v > 5):
            raise ValueError("feedback_score must be between 1 and 5")
        return v
    
    def __init__(self, **data):
        if data.get("timestamp") is None:
            data["timestamp"] = datetime.now(timezone.utc)
        super().__init__(**data)


class UserProfile(BaseModel):
    """ユーザープロファイル"""
    
    model_config = {"frozen": True}
    
    user_id: str
    plan: UserPlan = UserPlan.FREE
    conversations: tuple[ConversationRecord, ...] = ()
    created_at: datetime | None = None
    updated_at: datetime | None = None
    preferred_categories: tuple[str, ...] = ()
    
    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """ユーザーIDのバリデーション: 英数字とハイフンのみ、空不可"""
        if not v:
            raise ValueError("user_id must not be empty")
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9\-]{0,62}$", v):
            raise ValueError(
                "user_id must start with alphanumeric and contain only "
                "alphanumeric characters and hyphens (max 63 chars)"
            )
        return v
    
    def __init__(self, **data):
        if data.get("created_at") is None:
            data["created_at"] = datetime.now(timezone.utc)
        if data.get("updated_at") is None:
            data["updated_at"] = datetime.now(timezone.utc)
        super().__init__(**data)


class UserCreateRequest(BaseModel):
    """ユーザー作成リクエスト"""
    
    user_id: str
    
    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """ユーザーIDのバリデーション"""
        if not v:
            raise ValueError("user_id must not be empty")
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9\-]{0,62}$", v):
            raise ValueError(
                "user_id must start with alphanumeric and contain only "
                "alphanumeric characters and hyphens (max 63 chars)"
            )
        return v


class UserUpdatePlanRequest(BaseModel):
    """プラン更新リクエスト"""
    
    plan: UserPlan
    target_user_id: Optional[str] = None


class UserResponse(BaseModel):
    """ユーザーレスポンス"""
    
    user_id: str
    plan: UserPlan
    conversations: list[dict]
    created_at: datetime | None
    updated_at: datetime | None
    preferred_categories: list[str]
    
    @classmethod
    def from_profile(cls, profile: UserProfile) -> "UserResponse":
        """UserProfileからUserResponseを作成"""
        return cls(
            user_id=profile.user_id,
            plan=profile.plan,
            conversations=[c.model_dump() for c in profile.conversations],
            created_at=profile.created_at,
            updated_at=profile.updated_at,
            preferred_categories=list(profile.preferred_categories),
        )
