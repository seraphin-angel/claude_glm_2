"""
コンテンツ安全性チェックツール

入力/出力のガードレールチェックを行うツール。
プロンプトインジェクション、ジェイルブレイク、PII漏洩、攻撃的表現を検出。
"""

import re
from typing import Any

from langchain_core.tools import tool

from app.models.guardrails import RiskLevel, SafetyCheckResult, ViolationType


# 検出パターンの定義
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+all\s+(previous\s+)?instructions",
    r"disregard\s+(all\s+)?(previous\s+)?prompts?",
    r"you\s+are\s+now\s+in\s+(developer|admin|root)\s+mode",
    r"override\s+(your\s+)?programming",
    r"forget\s+(all\s+)?(previous\s+)?instructions",
    r"do\s+anything\s+now",
    r"new\s+directive:",
    r"system:\s*you\s+must",
    r"\[system\]",
    r"<\|im_start\|>",
]

JAILBREAK_PATTERNS = [
    r"act\s+as\s+if\s+you\s+were?",
    r"pretend\s+(you\s+are|to\s+be)",
    r"in\s+character\s+as",
    r"role[-\s]?play\s+as",
    r"imagine\s+you\s+are",
    r"you\s+are\s+now\s+(a|an)\s+\w+",
    r"simulate\s+(being|a)",
    r"persona:",
]

PII_PATTERNS = {
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone_jp": r"\b0\d{1,4}[-\s]?\d{1,4}[-\s]?\d{4}\b",
}

OFFENSIVE_PATTERNS = [
    # 日本語の暴言・差別的表現（サンプル）
    r"死ね",
    r"殺す",
    r"バカ",
    r"アホ",
    # 英語の攻撃的表現
    r"\bfuck\b",
    r"\bshit\b",
    r"\bdamn\b",
]


def _detect_patterns(content: str, patterns: list[str]) -> list[str]:
    """正規表現パターンを検出"""
    detected = []
    for pattern in patterns:
        if re.search(pattern, content, re.IGNORECASE):
            detected.append(pattern)
    return detected


def _detect_pii(content: str) -> tuple[list[str], list[str]]:
    """PIIを検出し、タイプと検出値を返す"""
    detected_types = []
    detected_values = []
    for pii_type, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, content)
        if matches:
            detected_types.append(pii_type)
            detected_values.extend(matches)
    return detected_types, detected_values


def _mask_pii(content: str) -> str:
    """PIIをマスキング"""
    masked = content
    # SSN: XXX-XX-XXXX → ***-**-****
    masked = re.sub(PII_PATTERNS["ssn"], "***-**-****", masked)
    # Credit Card: XXXX-XXXX-XXXX-XXXX → ****-****-****-****
    masked = re.sub(PII_PATTERNS["credit_card"], "****-****-****-****", masked)
    # Email: xxx@yyy.zzz → ***@***.***
    masked = re.sub(PII_PATTERNS["email"], "***@***.***", masked)
    # Phone: 0XX-XXXX-XXXX → ***-****-****
    masked = re.sub(PII_PATTERNS["phone_jp"], "***-****-****", masked)
    return masked


def _calculate_risk_level(
    prompt_injections: list[str],
    jailbreaks: list[str],
    pii_types: list[str],
    offensive: list[str],
) -> RiskLevel:
    """リスクレベルを計算"""
    if prompt_injections or jailbreaks:
        return RiskLevel.CRITICAL
    if pii_types:
        return RiskLevel.HIGH
    if offensive:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _calculate_confidence(
    prompt_injections: list[str],
    jailbreaks: list[str],
    pii_types: list[str],
    offensive: list[str],
) -> float:
    """信頼度を計算（検出数が多いほど高い）"""
    total_detections = (
        len(prompt_injections) + 
        len(jailbreaks) + 
        len(pii_types) + 
        len(offensive)
    )
    if total_detections == 0:
        return 0.95  # 安全と判定した場合の信頼度
    # 検出数に応じて信頼度を計算（最大 0.99）
    return min(0.99, 0.7 + (total_detections * 0.05))


@tool
def check_input_safety(content: str) -> dict[str, Any]:
    """入力コンテンツの安全性をチェックします。

    プロンプトインジェクション、ジェイルブレイク攻撃、攻撃的表現を検出します。

    Args:
        content: チェックする入力コンテンツ

    Returns:
        SafetyCheckResult を辞書形式で返す
    """
    # プロンプトインジェクション検出
    prompt_injections = _detect_patterns(content, PROMPT_INJECTION_PATTERNS)
    
    # ジェイルブレイク検出
    jailbreaks = _detect_patterns(content, JAILBREAK_PATTERNS)
    
    # 攻撃的表現検出
    offensive = _detect_patterns(content, OFFENSIVE_PATTERNS)
    
    # PII検出（入力では検出のみ、マスキングはしない）
    pii_types, _ = _detect_pii(content)
    
    # 違反タイプの収集
    violation_types = []
    violations = []
    
    if prompt_injections:
        violation_types.append(ViolationType.PROMPT_INJECTION)
        violations.append("プロンプトインジェクションの可能性がある入力を検出")
    
    if jailbreaks:
        violation_types.append(ViolationType.JAILBREAK)
        violations.append("ジェイルブレイク攻撃の可能性がある入力を検出")
    
    if offensive:
        violation_types.append(ViolationType.OFFENSIVE_CONTENT)
        violations.append("攻撃的表現を検出")
    
    if pii_types:
        violation_types.append(ViolationType.PII_LEAK)
        violations.append(f"個人情報の可能性があるデータを検出: {', '.join(pii_types)}")
    
    # リスクレベルと信頼度の計算
    risk_level = _calculate_risk_level(prompt_injections, jailbreaks, pii_types, offensive)
    confidence = _calculate_confidence(prompt_injections, jailbreaks, pii_types, offensive)
    
    is_safe = len(violation_types) == 0
    
    return SafetyCheckResult(
        is_safe=is_safe,
        risk_level=risk_level,
        violations=violations,
        violation_types=violation_types,
        sanitized_content=None,
        confidence=confidence,
    ).model_dump()


@tool
def check_output_safety(content: str) -> dict[str, Any]:
    """出力コンテンツの安全性をチェックします。

    PII漏洩、攻撃的表現を検出し、必要に応じてサニタイズします。

    Args:
        content: チェックする出力コンテンツ

    Returns:
        SafetyCheckResult を辞書形式で返す（sanitized_content にはマスキング済みコンテンツが含まれる）
    """
    # PII検出
    pii_types, pii_values = _detect_pii(content)
    
    # 攻撃的表現検出
    offensive = _detect_patterns(content, OFFENSIVE_PATTERNS)
    
    # 違反タイプの収集
    violation_types = []
    violations = []
    
    if pii_types:
        violation_types.append(ViolationType.PII_LEAK)
        violations.append(f"個人情報を検出: {', '.join(pii_types)}")
    
    if offensive:
        violation_types.append(ViolationType.OFFENSIVE_CONTENT)
        violations.append("攻撃的表現を検出")
    
    # サニタイズ（PIIをマスキング）
    sanitized_content = _mask_pii(content) if pii_types else None
    
    # リスクレベルと信頼度の計算
    risk_level = _calculate_risk_level([], [], pii_types, offensive)
    confidence = _calculate_confidence([], [], pii_types, offensive)
    
    is_safe = len(violation_types) == 0
    
    return SafetyCheckResult(
        is_safe=is_safe,
        risk_level=risk_level,
        violations=violations,
        violation_types=violation_types,
        sanitized_content=sanitized_content,
        confidence=confidence,
    ).model_dump()
