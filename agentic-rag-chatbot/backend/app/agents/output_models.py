from pydantic import BaseModel, Field


class ClassifyOutput(BaseModel):
    """質問分類の出力モデル"""

    category: str = Field(description="分類カテゴリ")
    confidence: float = Field(description="確信度 (0.0-1.0)")
    reason: str = Field(default="", description="分類理由")


class RelevanceOutput(BaseModel):
    """関連性評価の出力モデル"""

    is_relevant: bool = Field(description="関連性があるか")
    score: float = Field(description="関連性スコア (0.0-1.0)")
    relevant_doc_indices: list[int] = Field(
        default_factory=list, description="関連文書のインデックス"
    )
    reason: str = Field(default="", description="評価理由")


class QualityOutput(BaseModel):
    """品質チェックの出力モデル"""

    hallucination_score: float = Field(description="ハルシネーションスコア (0.0-1.0)")
    sufficiency_score: float = Field(description="充足性スコア (0.0-1.0)")
    issues: list[str] = Field(default_factory=list, description="問題点リスト")
    suggestions: str = Field(default="", description="改善提案")
