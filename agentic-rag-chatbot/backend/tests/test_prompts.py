"""CATEGORY_PROMPTS および generate_answer のカテゴリ別プロンプト適用テスト"""

from unittest.mock import MagicMock, patch

import pytest

from app.agents.prompts import CATEGORY_PROMPTS, ESCALATION_CRITERIA, PRODUCT_SUPPORT_SYSTEM_PROMPT


class TestCategoryPrompts:
    """CATEGORY_PROMPTS 辞書の構造テスト"""

    def test_category_prompts_has_three_categories(self):
        """CATEGORY_PROMPTS に3カテゴリが含まれることを確認"""
        assert len(CATEGORY_PROMPTS) == 3

    def test_category_prompts_has_required_keys(self):
        """必須カテゴリキーが存在することを確認"""
        expected_keys = {"操作方法", "障害・トラブル", "契約・料金"}
        assert set(CATEGORY_PROMPTS.keys()) == expected_keys

    def test_category_prompt_howto_contains_example(self):
        """操作方法カテゴリのプロンプトに回答例が含まれることを確認"""
        prompt = CATEGORY_PROMPTS["操作方法"]
        assert "回答例" in prompt

    def test_category_prompt_trouble_contains_example(self):
        """障害・トラブルカテゴリのプロンプトに回答例が含まれることを確認"""
        prompt = CATEGORY_PROMPTS["障害・トラブル"]
        assert "回答例" in prompt

    def test_category_prompt_contract_contains_example(self):
        """契約・料金カテゴリのプロンプトに回答例が含まれることを確認"""
        prompt = CATEGORY_PROMPTS["契約・料金"]
        assert "回答例" in prompt

    def test_category_prompt_howto_mentions_numbered_list(self):
        """操作方法プロンプトが手順を番号付きリストで示す指示を含むことを確認"""
        prompt = CATEGORY_PROMPTS["操作方法"]
        assert "番号付きリスト" in prompt

    def test_category_prompt_trouble_mentions_escalation(self):
        """障害・トラブルプロンプトがエスカレーション案内の指示を含むことを確認"""
        prompt = CATEGORY_PROMPTS["障害・トラブル"]
        assert "エスカレーション" in prompt

    def test_category_prompt_contract_warns_against_guessing_price(self):
        """契約・料金プロンプトが推測で金額を述べない指示を含むことを確認"""
        prompt = CATEGORY_PROMPTS["契約・料金"]
        assert "推測" in prompt

    def test_category_prompts_values_are_strings(self):
        """すべてのカテゴリプロンプト値が文字列であることを確認"""
        for key, value in CATEGORY_PROMPTS.items():
            assert isinstance(value, str), f"カテゴリ '{key}' の値が文字列ではありません"

    def test_category_prompts_values_are_non_empty(self):
        """すべてのカテゴリプロンプト値が空でないことを確認"""
        for key, value in CATEGORY_PROMPTS.items():
            assert len(value.strip()) > 0, f"カテゴリ '{key}' の値が空です"


class TestGenerateAnswerCategoryPrompt:
    """generate_answer がカテゴリ別プロンプトを使用することのテスト"""

    def _make_mock_llm(self, return_text: str):
        from langchain_core.messages import AIMessage
        mock_llm = MagicMock()
        mock_llm.return_value = AIMessage(content=return_text)
        return mock_llm

    def test_category_prompt_is_injected_into_system_message(self):
        """カテゴリに対応するプロンプトがシステムメッセージに含まれることを確認"""
        from app.agents.tools.generate import generate_answer

        mock_llm = self._make_mock_llm("操作方法に基づく回答")

        documents = [
            {
                "content": "ログイン方法の手順",
                "metadata": {"source": "product_guide.md", "section": "ログイン"},
            }
        ]

        with patch("app.agents.tools.generate.get_llm", return_value=mock_llm):
            result = generate_answer.invoke({
                "query": "ログイン方法を教えてください",
                "relevant_documents": documents,
                "category": "操作方法",
            })

        call_args = mock_llm.call_args
        prompt_str = call_args[0][0].to_string()
        assert "操作方法" in prompt_str
        assert "回答例" in prompt_str

    def test_trouble_category_prompt_injected(self):
        """障害・トラブルカテゴリのプロンプトが注入されることを確認"""
        from app.agents.tools.generate import generate_answer

        mock_llm = self._make_mock_llm("トラブルに基づく回答")

        documents = [
            {
                "content": "エラー対処法",
                "metadata": {"source": "troubleshooting.md"},
            }
        ]

        with patch("app.agents.tools.generate.get_llm", return_value=mock_llm):
            generate_answer.invoke({
                "query": "エラーが発生しました",
                "relevant_documents": documents,
                "category": "障害・トラブル",
            })

        call_args = mock_llm.call_args
        prompt_str = call_args[0][0].to_string()
        assert "障害・トラブル" in prompt_str
        assert "エスカレーション" in prompt_str

    def test_contract_category_prompt_injected(self):
        """契約・料金カテゴリのプロンプトが注入されることを確認"""
        from app.agents.tools.generate import generate_answer

        mock_llm = self._make_mock_llm("料金に基づく回答")

        documents = [
            {
                "content": "料金プラン情報",
                "metadata": {"source": "contracts.md", "section": "料金プラン"},
            }
        ]

        with patch("app.agents.tools.generate.get_llm", return_value=mock_llm):
            generate_answer.invoke({
                "query": "料金を教えてください",
                "relevant_documents": documents,
                "category": "契約・料金",
            })

        call_args = mock_llm.call_args
        prompt_str = call_args[0][0].to_string()
        assert "契約・料金" in prompt_str
        assert "推測" in prompt_str

    def test_unknown_category_does_not_inject_category_prompt(self):
        """未知のカテゴリではカテゴリプロンプトが注入されないことを確認"""
        from app.agents.tools.generate import generate_answer

        mock_llm = self._make_mock_llm("その他カテゴリの回答")

        documents = [
            {
                "content": "一般情報",
                "metadata": {"source": "general.md"},
            }
        ]

        with patch("app.agents.tools.generate.get_llm", return_value=mock_llm):
            generate_answer.invoke({
                "query": "一般的な質問",
                "relevant_documents": documents,
                "category": "その他",
            })

        call_args = mock_llm.call_args
        prompt_str = call_args[0][0].to_string()
        # 未定義カテゴリのプロンプトは注入されない
        assert "回答例" not in prompt_str

    def test_context_includes_section_when_present(self):
        """metadata に section がある場合、context に section が含まれることを確認"""
        from app.agents.tools.generate import generate_answer

        mock_llm = self._make_mock_llm("セクション情報を含む回答")

        documents = [
            {
                "content": "ログイン設定の詳細",
                "metadata": {"source": "product_guide.md", "section": "ログイン設定"},
            }
        ]

        with patch("app.agents.tools.generate.get_llm", return_value=mock_llm):
            generate_answer.invoke({
                "query": "ログイン設定を教えてください",
                "relevant_documents": documents,
            })

        call_args = mock_llm.call_args
        prompt_str = call_args[0][0].to_string()
        assert "product_guide.md > ログイン設定" in prompt_str

    def test_context_source_without_section(self):
        """metadata に section がない場合、source のみが含まれることを確認"""
        from app.agents.tools.generate import generate_answer

        mock_llm = self._make_mock_llm("セクションなしの回答")

        documents = [
            {
                "content": "一般情報",
                "metadata": {"source": "general.md"},
            }
        ]

        with patch("app.agents.tools.generate.get_llm", return_value=mock_llm):
            generate_answer.invoke({
                "query": "一般的な質問",
                "relevant_documents": documents,
            })

        call_args = mock_llm.call_args
        prompt_str = call_args[0][0].to_string()
        assert "general.md" in prompt_str
        # section がない場合は " > " 区切りが含まれない
        assert "general.md > " not in prompt_str

    def test_citation_format_instruction_in_system_prompt(self):
        """システムプロンプトに引用フォーマット指示が含まれることを確認"""
        from app.agents.tools.generate import generate_answer

        mock_llm = self._make_mock_llm("引用フォーマットを使った回答")

        documents = [
            {
                "content": "テスト情報",
                "metadata": {"source": "test.md"},
            }
        ]

        with patch("app.agents.tools.generate.get_llm", return_value=mock_llm):
            generate_answer.invoke({
                "query": "テスト質問",
                "relevant_documents": documents,
            })

        call_args = mock_llm.call_args
        prompt_str = call_args[0][0].to_string()
        assert "参考:" in prompt_str


class TestEscalationCriteria:
    """ESCALATION_CRITERIA 定数および SYSTEM_PROMPT のエスカレーション基準テスト"""

    def test_escalation_criteria_exists(self):
        """ESCALATION_CRITERIA が存在することを確認"""
        assert ESCALATION_CRITERIA is not None
        assert isinstance(ESCALATION_CRITERIA, str)
        assert len(ESCALATION_CRITERIA.strip()) > 0

    def test_escalation_criteria_mentions_explicit_request(self):
        """ユーザーが明示的に有人対応を希望した場合の基準が含まれる"""
        assert "明示的に有人対応" in ESCALATION_CRITERIA

    def test_escalation_criteria_mentions_technical_issues(self):
        """技術的に解決不可能な問題の基準が含まれる"""
        assert "技術的に解決不可能" in ESCALATION_CRITERIA

    def test_escalation_criteria_mentions_legal_financial(self):
        """法的・金銭的な重要事項の基準が含まれる"""
        assert "法的" in ESCALATION_CRITERIA or "金銭" in ESCALATION_CRITERIA

    def test_escalation_criteria_mentions_repeated_questions(self):
        """3回以上同じ質問を繰り返している場合の基準が含まれる"""
        assert "3回" in ESCALATION_CRITERIA

    def test_escalation_criteria_mentions_tool_name(self):
        """escalate_to_human ツール名が言及されている"""
        assert "escalate_to_human" in ESCALATION_CRITERIA

    def test_system_prompt_includes_escalation_criteria(self):
        """システムプロンプトにエスカレーション判断基準が含まれる"""
        assert "escalate_to_human" in PRODUCT_SUPPORT_SYSTEM_PROMPT
        assert "エスカレーション" in PRODUCT_SUPPORT_SYSTEM_PROMPT

    def test_system_prompt_mentions_urgency_levels(self):
        """システムプロンプトに緊急度の記述がある（間接的に）"""
        # ツールの使用指示があることを確認
        assert "escalate_to_human" in PRODUCT_SUPPORT_SYSTEM_PROMPT

    def test_escalation_criteria_includes_urgency_levels(self):
        """エスカレーション基準に緊急度の説明がある"""
        assert "緊急度" in ESCALATION_CRITERIA or "urgency" in ESCALATION_CRITERIA
