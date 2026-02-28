"""プロンプト管理モジュール

動的プロンプト読み込みと後方互換性のあるフォールバックを提供。
"""

import logging
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

# ============== フォールバック用のハードコードされたプロンプト ==============
# PromptServiceが利用できない場合やデータファイルがない場合に使用

_FALLBACK_CATEGORY_PROMPTS = {
    "操作方法": """## カテゴリ: 操作方法
ユーザーは製品の使い方や設定方法について質問しています。
- 手順は番号付きリストで明確に示してください
- スクリーンショットの位置を案内する場合は「画面上部の○○ボタン」等の表現を使ってください
- 関連する設定項目があれば併せて案内してください

### 回答例
Q: ログイン方法を教えてください
A: ログイン方法は以下の通りです。
1. トップページ右上の「ログイン」ボタンをクリックします
2. メールアドレスとパスワードを入力します
3. 「ログイン」ボタンをクリックします
【参考: product_guide.md > ログイン】""",

    "障害・トラブル": """## カテゴリ: 障害・トラブル
ユーザーはエラーや不具合について問い合わせています。
- まず症状を正確に理解し、原因を特定してください
- 解決手順は段階的に示してください
- 解決しない場合のエスカレーション先を案内してください

### 回答例
Q: ログインできません
A: ログインできない場合、以下の手順をお試しください。
1. メールアドレスが正しいか確認してください
2. パスワードをリセットしてみてください
3. ブラウザのキャッシュをクリアしてください
上記で解決しない場合は、サポート窓口までご連絡ください。
【参考: troubleshooting.md > ログインエラー】""",

    "契約・料金": """## カテゴリ: 契約・料金
ユーザーはプランや料金について質問しています。
- 具体的な金額や条件は必ず参考情報から引用してください
- 推測で金額を述べないでください
- 契約変更の手順がある場合は明確に示してください

### 回答例
Q: プランの料金を教えてください
A: 各プランの料金は以下の通りです。
- ベーシックプラン: 月額980円
- プロプラン: 月額1,980円
詳細は契約ページをご確認ください。
【参考: contracts.md > 料金プラン】""",
}

_FALLBACK_ESCALATION_CRITERIA = """
## エスカレーション判断基準

以下の場合は `escalate_to_human` ツールを使用して有人サポートにエスカレーションしてください：

1. **ユーザーが明示的に有人対応を希望した場合**
   - 「オペレーターに代わって」「人間と話したい」などの発言

2. **技術的に解決不可能な問題**
   - システムバグや障害が疑われる場合
   - ナレッジベースに解決策が存在しない技術的問題
   - アカウントの復旧が必要な場合

3. **法的・金銭的な重要事項**
   - 返金リクエスト
   - 契約解除・解約手続き
   - 請求に関する異議申し立て
   - 法的な責任が伴う判断が必要な場合

4. **ユーザーが同じ質問を3回以上繰り返している場合**
   - AIでの解決が困難と判断される場合

### エスカレーション時の注意点
- 必ず `escalate_to_human` ツールを使用し、適切な緊急度（urgency）を設定すること
- エスカレーションの理由（reason）を明確に記載すること
- 会話の要約（summary）を簡潔にまとめること
- エスカレーション後は、ユーザーに担当者からの連絡を待つよう案内すること
"""

_FALLBACK_SYSTEM_PROMPT = """あなたは製品サポートの AI アシスタントです。
ユーザーからの質問に対して、正確で丁寧な回答を提供します。

## あなたの役割
- 製品に関する質問に正確に回答する
- 必要に応じてナレッジベースを検索し、エビデンスに基づいた回答を行う
- 曖昧な質問には確認を行い、正確な回答につなげる

## 対応カテゴリ
1. **操作方法**: 製品の使い方、設定方法、機能の説明
2. **障害・トラブル**: エラー、不具合、動作問題の解決
3. **契約・料金**: プラン、料金、契約、解約に関する情報
4. **その他**: 上記以外の製品関連の質問

## ワークフロー
1. まず `classify_query` で質問を分類する
2. out_of_scope の場合は、サポート範囲外であることを丁寧に伝え、製品に関する質問を促す
3. 分類に成功したら、必要に応じて `rewrite_query` でクエリを最適化する
4. `search_knowledge` でナレッジベースから関連情報を検索する
5. `check_relevance` で検索結果の関連性を確認する
6. 関連性が十分であれば `generate_answer` で回答を生成する
7. 関連性が不十分な場合は `ask_human` でユーザーに追加情報を求める
8. `check_quality` で生成された回答の品質を確認する
9. 品質チェックに合格したら回答を返す
10. 品質チェックに不合格の場合は、検索条件を変更して再試行するか、人間に確認する
11. `check_quality` 不合格時のリトライは最大2回まで。3回目以降は `escalate_to_human` で有人サポートにエスカレーションすること

## エスカレーション判断基準

以下の場合は `escalate_to_human` ツールを使用して有人サポートにエスカレーションしてください：

1. **ユーザーが明示的に有人対応を希望した場合**
   - 「オペレーターに代わって」「人間と話したい」などの発言

2. **技術的に解決不可能な問題**
   - システムバグや障害が疑われる場合
   - ナレッジベースに解決策が存在しない技術的問題
   - アカウントの復旧が必要な場合

3. **法的・金銭的な重要事項**
   - 返金リクエスト
   - 契約解除・解約手続き
   - 請求に関する異議申し立て

4. **ユーザーが同じ質問を3回以上繰り返している場合**
   - AIでの解決が困難と判断される場合

## 重要なルール
- **必ず**ナレッジベースの検索結果に基づいて回答すること
- 参考情報にない内容は推測で回答しないこと
- 質問が曖昧な場合は `ask_human` ツールで聞き返すこと
- 製品サポートの範囲外の質問（天気、ニュース等）には対応しないこと
- 常に丁寧で分かりやすい日本語で回答すること
- 手順を説明する場合は番号付きリストを使用すること
- エスカレーションが必要な場合は `escalate_to_human` ツールを使用すること

## 回答フォーマット
- 簡潔かつ正確に回答する
- 必要に応じて手順を番号付きで列挙する
- 関連する追加情報がある場合は最後に案内する
- 「ご不明な点がございましたら、お気軽にお問い合わせください。」で締める
"""

# カテゴリ名とプロンプトIDのマッピング
_CATEGORY_TO_PROMPT_ID = {
    "操作方法": "category_operation",
    "障害・トラブル": "category_troubleshooting",
    "契約・料金": "category_contract",
}


@lru_cache(maxsize=1)
def _get_prompt_service():
    """PromptServiceを遅延インポートして取得（キャッシュ付き）"""
    try:
        from app.services.prompt_service import PromptService
        return PromptService.get_instance()
    except ImportError as e:
        logger.warning("PromptService module not available: %s", e)
        return None
    except Exception as e:
        logger.error(
            "Failed to get PromptService: %s",
            type(e).__name__,
            exc_info=True,
        )
        return None


def get_system_prompt() -> str:
    """システムプロンプトを取得

    PromptServiceから動的に取得を試み、失敗した場合はフォールバック値を返す。

    Returns:
        システムプロンプト文字列
    """
    service = _get_prompt_service()
    if service:
        prompt = service.get_prompt("system")
        if prompt:
            return prompt.content

    logger.warning("Using fallback system prompt")
    return _FALLBACK_SYSTEM_PROMPT


def get_category_prompt(category: str) -> str:
    """カテゴリ別プロンプトを取得

    PromptServiceから動的に取得を試み、失敗した場合はフォールバック値を返す。

    Args:
        category: カテゴリ名（"操作方法", "障害・トラブル", "契約・料金"）

    Returns:
        カテゴリ別プロンプト文字列
    """
    prompt_id = _CATEGORY_TO_PROMPT_ID.get(category)

    service = _get_prompt_service()
    if service and prompt_id:
        prompt = service.get_prompt(prompt_id)
        if prompt:
            return prompt.content

    # フォールバック
    logger.warning(f"Using fallback prompt for category: {category}")
    return _FALLBACK_CATEGORY_PROMPTS.get(category, "")


def get_escalation_criteria() -> str:
    """エスカレーション判断基準プロンプトを取得

    PromptServiceから動的に取得を試み、失敗した場合はフォールバック値を返す。

    Returns:
        エスカレーション判断基準プロンプト文字列
    """
    service = _get_prompt_service()
    if service:
        prompt = service.get_prompt("escalation_criteria")
        if prompt:
            return prompt.content

    logger.warning("Using fallback escalation criteria prompt")
    return _FALLBACK_ESCALATION_CRITERIA


# ============== 後方互換性のための定数 ==============
# 既存のコードがこれらを直接参照している場合に使用

CATEGORY_PROMPTS = _FALLBACK_CATEGORY_PROMPTS
ESCALATION_CRITERIA = _FALLBACK_ESCALATION_CRITERIA
PRODUCT_SUPPORT_SYSTEM_PROMPT = _FALLBACK_SYSTEM_PROMPT


# ============== P3-54: パーソナライゼーション機能 ==============

def get_personalized_system_prompt(user_profile=None) -> str:
    """ユーザープロファイルに基づくパーソナライズされたシステムプロンプトを取得

    Args:
        user_profile: UserProfile オブジェクト（オプション）
            - plan: ユーザープラン（free/paid）
            - preferred_categories: ユーザーがよく質問するカテゴリ
            - conversations: 過去の会話履歴

    Returns:
        パーソナライズされたシステムプロンプト
    """
    base_prompt = get_system_prompt()

    if user_profile is None:
        return base_prompt

    # パーソナライゼーション情報を構築
    personalization_parts = []

    # プランに基づく情報
    plan = getattr(user_profile, "plan", None)
    if plan:
        plan_str = plan.value if hasattr(plan, "value") else str(plan)
        if plan_str == "free":
            personalization_parts.append("""
## ユーザープラン情報
このユーザーは無料プランを利用中です。
- 一部の高度な機能は制限されている場合があります
- プランのアップグレードを提案する場合は、丁寧に案内してください
""")
        elif plan_str == "paid":
            personalization_parts.append("""
## ユーザープラン情報
このユーザーは有料プランを利用中です。
- すべての機能を利用可能です
- 高度なサポートを提供してください
""")

    # 過去の質問カテゴリに基づく情報
    preferred_categories = getattr(user_profile, "preferred_categories", None)
    if preferred_categories and len(preferred_categories) > 0:
        categories_str = "、".join(preferred_categories)
        personalization_parts.append(f"""
## ユーザーの関心分野
このユーザーは以下の分野について頻繁に質問しています: {categories_str}
- これらの分野に関する質問には特に丁寧に回答してください
- 関連する情報があれば積極的に提供してください
""")

    # パーソナライゼーション情報を追加
    if personalization_parts:
        personalization_context = "\n".join(personalization_parts)
        return f"{base_prompt}\n\n---\n# パーソナライゼーション情報{personalization_context}"

    return base_prompt


def get_user_context_summary(user_profile=None) -> str:
    """ユーザーのコンテキスト要約を取得

    Args:
        user_profile: UserProfile オブジェクト

    Returns:
        ユーザーコンテキストの要約文字列
    """
    if user_profile is None:
        return ""

    parts = []

    plan = getattr(user_profile, "plan", None)
    if plan:
        plan_str = plan.value if hasattr(plan, "value") else str(plan)
        parts.append(f"プラン: {plan_str}")

    preferred_categories = getattr(user_profile, "preferred_categories", None)
    if preferred_categories and len(preferred_categories) > 0:
        parts.append(f"関心分野: {', '.join(preferred_categories)}")

    conversations = getattr(user_profile, "conversations", None)
    if conversations:
        parts.append(f"過去の会話数: {len(conversations)}")

    return " | ".join(parts) if parts else ""
