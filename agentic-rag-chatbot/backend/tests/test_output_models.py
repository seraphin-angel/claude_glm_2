"""出力モデルのテスト"""

import pytest
from pydantic import ValidationError

from app.agents.output_models import ClassifyOutput, QualityOutput, RelevanceOutput


class TestClassifyOutput:
    def test_valid_creation(self):
        output = ClassifyOutput(category="操作方法", confidence=0.95, reason="テスト")
        assert output.category == "操作方法"
        assert output.confidence == 0.95

    def test_default_reason(self):
        output = ClassifyOutput(category="unclear", confidence=0.0)
        assert output.reason == ""

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            ClassifyOutput()


class TestRelevanceOutput:
    def test_valid_creation(self):
        output = RelevanceOutput(
            is_relevant=True,
            score=0.85,
            relevant_doc_indices=[0, 1],
            reason="関連あり",
        )
        assert output.is_relevant is True
        assert output.score == 0.85

    def test_default_fields(self):
        output = RelevanceOutput(is_relevant=False, score=0.1)
        assert output.relevant_doc_indices == []
        assert output.reason == ""


class TestQualityOutput:
    def test_valid_creation(self):
        output = QualityOutput(
            hallucination_score=0.9,
            sufficiency_score=0.8,
            issues=["issue1"],
            suggestions="改善提案",
        )
        assert output.hallucination_score == 0.9
        assert output.issues == ["issue1"]

    def test_default_fields(self):
        output = QualityOutput(hallucination_score=0.5, sufficiency_score=0.5)
        assert output.issues == []
        assert output.suggestions == ""
