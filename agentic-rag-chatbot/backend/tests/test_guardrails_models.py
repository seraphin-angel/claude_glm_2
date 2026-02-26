"""
ガードレールモデルのユニットテスト

テスト方針:
- Pydantic BaseModel のバリデーションをテスト
- Enum 値の正確性をテスト
- 境界値テストを含む
"""

import pytest
from pydantic import ValidationError

from app.models.guardrails import RiskLevel, ViolationType, SafetyCheckResult


class TestRiskLevelEnum:
    """RiskLevel Enum のテスト"""

    def test_risk_level_enum_values(self):
        """RiskLevel が正しい値を持つことを確認"""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"

    def test_risk_level_count(self):
        """RiskLevel が4つの値を持つことを確認"""
        assert len(RiskLevel) == 4

    def test_risk_level_string_conversion(self):
        """RiskLevel が文字列として扱えることを確認"""
        assert RiskLevel.LOW == "low"
        assert RiskLevel.CRITICAL == "critical"


class TestViolationTypeEnum:
    """ViolationType Enum のテスト"""

    def test_violation_type_enum_values(self):
        """ViolationType が正しい値を持つことを確認"""
        assert ViolationType.PROMPT_INJECTION.value == "prompt_injection"
        assert ViolationType.JAILBREAK.value == "jailbreak"
        assert ViolationType.PII_LEAK.value == "pii_leak"
        assert ViolationType.OFFENSIVE_CONTENT.value == "offensive_content"
        assert ViolationType.OUT_OF_SCOPE.value == "out_of_scope"

    def test_violation_type_count(self):
        """ViolationType が5つの値を持つことを確認"""
        assert len(ViolationType) == 5

    def test_violation_type_string_conversion(self):
        """ViolationType が文字列として扱えることを確認"""
        assert ViolationType.PROMPT_INJECTION == "prompt_injection"
        assert ViolationType.PII_LEAK == "pii_leak"


class TestSafetyCheckResult:
    """SafetyCheckResult BaseModel のテスト"""

    def test_safety_check_result_valid(self):
        """有効な SafetyCheckResult が作成できることを確認"""
        result = SafetyCheckResult(
            is_safe=True,
            risk_level=RiskLevel.LOW,
            violations=[],
            violation_types=[],
            sanitized_content=None,
            confidence=0.95
        )
        assert result.is_safe is True
        assert result.risk_level == RiskLevel.LOW
        assert result.violations == []
        assert result.violation_types == []
        assert result.sanitized_content is None
        assert result.confidence == 0.95

    def test_safety_check_result_with_violations(self):
        """違反がある SafetyCheckResult が作成できることを確認"""
        result = SafetyCheckResult(
            is_safe=False,
            risk_level=RiskLevel.HIGH,
            violations=["プロンプトインジェクションの可能性"],
            violation_types=[ViolationType.PROMPT_INJECTION],
            sanitized_content="[SANITIZED]",
            confidence=0.88
        )
        assert result.is_safe is False
        assert result.risk_level == RiskLevel.HIGH
        assert len(result.violations) == 1
        assert len(result.violation_types) == 1
        assert result.sanitized_content == "[SANITIZED]"

    def test_safety_check_result_confidence_validation_below_zero(self):
        """confidence が 0.0 未満の場合に ValidationError が発生することを確認"""
        with pytest.raises(ValidationError) as exc_info:
            SafetyCheckResult(
                is_safe=True,
                risk_level=RiskLevel.LOW,
                confidence=-0.1
            )
        assert "confidence" in str(exc_info.value)

    def test_safety_check_result_confidence_validation_above_one(self):
        """confidence が 1.0 を超える場合に ValidationError が発生することを確認"""
        with pytest.raises(ValidationError) as exc_info:
            SafetyCheckResult(
                is_safe=True,
                risk_level=RiskLevel.LOW,
                confidence=1.1
            )
        assert "confidence" in str(exc_info.value)

    def test_safety_check_result_confidence_boundary_zero(self):
        """confidence が 0.0 の場合に有効であることを確認"""
        result = SafetyCheckResult(
            is_safe=False,
            risk_level=RiskLevel.CRITICAL,
            confidence=0.0
        )
        assert result.confidence == 0.0

    def test_safety_check_result_confidence_boundary_one(self):
        """confidence が 1.0 の場合に有効であることを確認"""
        result = SafetyCheckResult(
            is_safe=True,
            risk_level=RiskLevel.LOW,
            confidence=1.0
        )
        assert result.confidence == 1.0

    def test_safety_check_result_optional_sanitized_content(self):
        """sanitized_content が Optional であることを確認"""
        # None で作成
        result_none = SafetyCheckResult(
            is_safe=True,
            risk_level=RiskLevel.LOW,
            confidence=0.9
        )
        assert result_none.sanitized_content is None

        # 文字列で作成
        result_str = SafetyCheckResult(
            is_safe=False,
            risk_level=RiskLevel.MEDIUM,
            sanitized_content="マスキング済み",
            confidence=0.8
        )
        assert result_str.sanitized_content == "マスキング済み"

    def test_safety_check_result_default_empty_lists(self):
        """violations と violation_types がデフォルトで空リストになることを確認"""
        result = SafetyCheckResult(
            is_safe=True,
            risk_level=RiskLevel.LOW,
            confidence=0.95
        )
        assert result.violations == []
        assert result.violation_types == []

    def test_safety_check_result_missing_required_fields(self):
        """必須フィールドが欠落している場合に ValidationError が発生することを確認"""
        with pytest.raises(ValidationError) as exc_info:
            SafetyCheckResult()  # 全ての必須フィールドが欠落
        errors = exc_info.value.errors()
        field_names = {e["loc"][0] for e in errors}
        assert "is_safe" in field_names
        assert "risk_level" in field_names
        assert "confidence" in field_names

    def test_safety_check_result_model_dump(self):
        """model_dump() で辞書に変換できることを確認"""
        result = SafetyCheckResult(
            is_safe=False,
            risk_level=RiskLevel.HIGH,
            violations=["PII漏洩の可能性"],
            violation_types=[ViolationType.PII_LEAK],
            sanitized_content="My SSN is ***-**-****",
            confidence=0.92
        )
        data = result.model_dump()
        assert data["is_safe"] is False
        assert data["risk_level"] == RiskLevel.HIGH
        assert data["violations"] == ["PII漏洩の可能性"]
        assert data["confidence"] == 0.92

    def test_safety_check_result_model_json_serialization(self):
        """JSON シリアライゼーションが正しく動作することを確認"""
        result = SafetyCheckResult(
            is_safe=True,
            risk_level=RiskLevel.LOW,
            confidence=0.99
        )
        json_str = result.model_dump_json()
        assert '"is_safe":true' in json_str or '"is_safe": true' in json_str
        assert '"confidence":0.99' in json_str or '"confidence": 0.99' in json_str
