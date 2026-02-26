"""ガードレール API エンドポイント"""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.models.guardrails import RiskLevel, ViolationType
from app.services.guardrails_service import GuardrailsService

router = APIRouter(prefix="/guardrails", tags=["guardrails"])


# ---------------------------------------------------------------------------
# リクエスト/レスポンスモデル
# ---------------------------------------------------------------------------


class CheckInputRequest(BaseModel):
    """入力チェックリクエスト"""

    content: str = Field(..., min_length=1, max_length=10000, description="チェックするコンテンツ")
    category: str | None = Field(None, description="カテゴリ（out_of_scope チェック用）")


class CheckOutputRequest(BaseModel):
    """出力チェックリクエスト"""

    content: str = Field(..., min_length=1, max_length=50000, description="チェックするコンテンツ")


class RedTeamRequest(BaseModel):
    """レッドチーミングテストリクエスト"""

    test_cases: list[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="テストケースのリスト",
    )


class SafetyCheckResponse(BaseModel):
    """安全性チェックレスポンス"""

    is_safe: bool = Field(..., description="安全かどうか")
    risk_level: str = Field(..., description="リスクレベル")
    violations: list[str] = Field(default_factory=list, description="違反内容のリスト")
    violation_types: list[str] = Field(default_factory=list, description="違反タイプのリスト")
    sanitized_content: str | None = Field(None, description="サニタイズ済みコンテンツ")
    confidence: float = Field(..., ge=0.0, le=1.0, description="信頼度")


class RedTeamResponse(BaseModel):
    """レッドチーミングテストレスポンス"""

    results: list[SafetyCheckResponse] = Field(..., description="テスト結果のリスト")
    summary: dict[str, Any] = Field(..., description="テスト結果のサマリー")


# ---------------------------------------------------------------------------
# エンドポイント
# ---------------------------------------------------------------------------


@router.post("/check-input", response_model=SafetyCheckResponse)
async def check_input(request: CheckInputRequest) -> SafetyCheckResponse:
    """入力コンテンツの安全性をチェック

    プロンプトインジェクション、ジェイルブレイク、攻撃的表現を検出します。
    """
    service = GuardrailsService.get_instance()
    result = service.check_input(request.content, request.category)

    return SafetyCheckResponse(
        is_safe=result["is_safe"],
        risk_level=result["risk_level"],
        violations=result.get("violations", []),
        violation_types=result.get("violation_types", []),
        sanitized_content=result.get("sanitized_content"),
        confidence=result.get("confidence", 0.0),
    )


@router.post("/check-output", response_model=SafetyCheckResponse)
async def check_output(request: CheckOutputRequest) -> SafetyCheckResponse:
    """出力コンテンツの安全性をチェック

    PII漏洩、攻撃的表現を検出し、必要に応じてサニタイズします。
    """
    service = GuardrailsService.get_instance()
    result = service.check_output(request.content)

    return SafetyCheckResponse(
        is_safe=result["is_safe"],
        risk_level=result["risk_level"],
        violations=result.get("violations", []),
        violation_types=result.get("violation_types", []),
        sanitized_content=result.get("sanitized_content"),
        confidence=result.get("confidence", 0.0),
    )


@router.post("/red-team", response_model=RedTeamResponse)
async def run_red_team_test(request: RedTeamRequest) -> RedTeamResponse:
    """レッドチーミングテストを実行

    複数のテストケースに対してガードレールチェックを一括実行し、
    結果のサマリーを返します。
    """
    service = GuardrailsService.get_instance()
    results = []

    safe_count = 0
    unsafe_count = 0
    violations_by_type: dict[str, int] = {}

    for test_case in request.test_cases:
        result = service.check_input(test_case)

        response = SafetyCheckResponse(
            is_safe=result["is_safe"],
            risk_level=result["risk_level"],
            violations=result.get("violations", []),
            violation_types=result.get("violation_types", []),
            sanitized_content=result.get("sanitized_content"),
            confidence=result.get("confidence", 0.0),
        )
        results.append(response)

        if result["is_safe"]:
            safe_count += 1
        else:
            unsafe_count += 1
            for vt in result.get("violation_types", []):
                violations_by_type[vt] = violations_by_type.get(vt, 0) + 1

    summary = {
        "total": len(request.test_cases),
        "safe": safe_count,
        "unsafe": unsafe_count,
        "detection_rate": unsafe_count / len(request.test_cases) if request.test_cases else 0,
        "violations_by_type": violations_by_type,
    }

    return RedTeamResponse(results=results, summary=summary)
