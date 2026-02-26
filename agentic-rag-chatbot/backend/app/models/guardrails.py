"""
ガードレール関連のモデル定義

入力/出力の安全性チェック結果を表現するデータモデル。
"""

from enum import Enum

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """リスクレベル"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ViolationType(str, Enum):
    """違反タイプ"""
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    PII_LEAK = "pii_leak"
    OFFENSIVE_CONTENT = "offensive_content"
    OUT_OF_SCOPE = "out_of_scope"


class SafetyCheckResult(BaseModel):
    """安全性チェック結果"""
    
    is_safe: bool = Field(..., description="安全かどうか")
    risk_level: RiskLevel = Field(..., description="リスクレベル")
    violations: list[str] = Field(default_factory=list, description="違反内容のリスト")
    violation_types: list[ViolationType] = Field(default_factory=list, description="違反タイプのリスト")
    sanitized_content: str | None = Field(None, description="サニタイズ済みコンテンツ")
    confidence: float = Field(..., ge=0.0, le=1.0, description="信頼度 (0.0-1.0)")
