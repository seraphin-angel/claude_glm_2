"""P3-55: A/Bテスト基盤 - 実験モデル定義"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator


class ExperimentStatus(str, Enum):
    """実験ステータス"""
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"


class MetricType(str, Enum):
    """指標タイプ"""
    RESPONSE_QUALITY = "response_quality"
    FEEDBACK_SCORE = "feedback_score"
    RESOLUTION_RATE = "resolution_rate"


class Variant(BaseModel):
    """バリアントモデル（A/Bテストの分岐）"""
    
    model_config = {"frozen": True}
    
    variant_id: str
    name: str
    weight: float
    config: dict = {}
    
    @field_validator("weight")
    @classmethod
    def validate_weight(cls, v: float) -> float:
        """重みは0〜1の範囲である必要がある"""
        if not 0 <= v <= 1:
            raise ValueError("weight must be between 0 and 1")
        return v


class Experiment(BaseModel):
    """実験モデル"""
    
    model_config = {"frozen": True}
    
    experiment_id: str
    name: str
    description: str = ""
    variants: list[Variant]
    status: ExperimentStatus = ExperimentStatus.DRAFT
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    metrics: list[MetricType] = []
    
    @field_validator("experiment_id")
    @classmethod
    def validate_experiment_id(cls, v: str) -> str:
        """実験IDは空であってはならない"""
        if not v or not v.strip():
            raise ValueError("experiment_id must not be empty")
        return v
    
    @field_validator("variants")
    @classmethod
    def validate_variants(cls, v: list[Variant]) -> list[Variant]:
        """バリアントは最低2つ必要"""
        if len(v) < 2:
            raise ValueError("experiment must have at least 2 variants")
        return v
    
    @model_validator(mode="after")
    def validate_variant_weights(self) -> "Experiment":
        """バリアントの重みの合計が1.0に近いか確認（許容誤差 0.01）"""
        total_weight = sum(v.weight for v in self.variants)
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(
                f"variant weights must sum to 1.0 (got {total_weight})"
            )
        return self


class ExperimentMetric(BaseModel):
    """実験指標モデル（記録された指標）"""
    
    model_config = {"frozen": True}
    
    experiment_id: str
    variant_id: str
    user_id: str
    metric_type: MetricType
    value: float
    timestamp: datetime = datetime.now()


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------

class VariantCreateRequest(BaseModel):
    """バリアント作成リクエスト"""
    
    variant_id: str
    name: str
    weight: float
    config: dict = {}
    
    @field_validator("weight")
    @classmethod
    def validate_weight(cls, v: float) -> float:
        """重みは0〜1の範囲である必要がある"""
        if not 0 <= v <= 1:
            raise ValueError("weight must be between 0 and 1")
        return v


class ExperimentCreateRequest(BaseModel):
    """実験作成リクエスト"""
    
    experiment_id: str
    name: str
    description: str = ""
    variants: list[VariantCreateRequest]
    metrics: list[MetricType] = []
    
    @field_validator("experiment_id")
    @classmethod
    def validate_experiment_id(cls, v: str) -> str:
        """実験IDは空であってはならない"""
        if not v or not v.strip():
            raise ValueError("experiment_id must not be empty")
        return v
    
    @field_validator("variants")
    @classmethod
    def validate_variants(cls, v: list[VariantCreateRequest]) -> list[VariantCreateRequest]:
        """バリアントは最低2つ必要"""
        if len(v) < 2:
            raise ValueError("experiment must have at least 2 variants")
        return v


class VariantAssignRequest(BaseModel):
    """バリアント割り当てリクエスト（experiment_idはパスパラメータ）"""
    
    user_id: str


class MetricRecordRequest(BaseModel):
    """指標記録リクエスト（experiment_idはパスパラメータ）"""
    
    variant_id: str
    user_id: str
    metric_type: MetricType
    value: float


class ExperimentStatusUpdateRequest(BaseModel):
    """実験ステータス更新リクエスト"""
    
    status: ExperimentStatus
