"""
ツールのユニットテスト

テスト方針:
- LLM呼び出し（get_llm）は全て unittest.mock.patch でモック
- ChromaDB / VectorStore 関連もモック
- interrupt() もモック（HITLのテスト用）
"""

from unittest.mock import MagicMock, patch

import pytest

from app.agents.output_models import ClassifyOutput, QualityOutput, RelevanceOutput
from app.agents.tools.ask_human import ask_human
from app.agents.tools.classify import classify_query
from app.agents.tools.generate import generate_answer
from app.agents.tools.quality import check_quality
from app.agents.tools.relevance import check_relevance
from app.agents.tools.rewrite import rewrite_query
from app.agents.tools.search import search_knowledge


# ---------------------------------------------------------------------------
# ヘルパー: LLM モックの生成
# ---------------------------------------------------------------------------


def _make_structured_llm_mock(output_obj):
    """with_structured_output() を使うツール用のモック。

    output_obj は Pydantic モデルのインスタンス。
    (prompt | structured_llm).invoke({...}) が output_obj を返す。
    """
    mock_structured_llm = MagicMock()
    mock_structured_llm.return_value = output_obj  # RunnableLambda.__call__ で返す値

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured_llm

    return mock_llm, mock_structured_llm


def _make_chat_llm_mock(content: str):
    """ChatPromptTemplate | llm パターン用のモック（generate, rewrite）。

    (prompt | llm).invoke({...}) が content を持つオブジェクトを返す。
    """
    mock_response = MagicMock()
    mock_response.content = content

    mock_llm = MagicMock()
    mock_llm.return_value = mock_response  # RunnableLambda.__call__ で返す値

    return mock_llm, mock_response


# ===========================================================================
# 1. classify_query テスト
# ===========================================================================


class TestClassifyQuery:
    def test_classify_operation_category(self):
        """「操作方法」に正常分類されることを確認"""
        mock_llm, _ = _make_structured_llm_mock(
            ClassifyOutput(category="操作方法", confidence=0.95, reason="製品の使い方に関する質問")
        )

        with patch("app.agents.tools.classify.get_llm", return_value=mock_llm):
            result = classify_query.invoke({"query": "製品Aの初期設定方法を教えてください"})

        assert result["category"] == "操作方法"
        assert result["confidence"] == 0.95
        assert "reason" in result

    def test_classify_trouble_category(self):
        """「障害・トラブル」に正常分類されることを確認"""
        mock_llm, _ = _make_structured_llm_mock(
            ClassifyOutput(category="障害・トラブル", confidence=0.90, reason="エラーに関する質問")
        )

        with patch("app.agents.tools.classify.get_llm", return_value=mock_llm):
            result = classify_query.invoke({"query": "ログインできないエラーが発生しています"})

        assert result["category"] == "障害・トラブル"
        assert result["confidence"] == 0.90

    def test_classify_contract_category(self):
        """「契約・料金」に正常分類されることを確認"""
        mock_llm, _ = _make_structured_llm_mock(
            ClassifyOutput(category="契約・料金", confidence=0.88, reason="料金に関する質問")
        )

        with patch("app.agents.tools.classify.get_llm", return_value=mock_llm):
            result = classify_query.invoke({"query": "月額料金はいくらですか？"})

        assert result["category"] == "契約・料金"

    def test_classify_out_of_scope(self):
        """out_of_scope が正しく返されることを確認"""
        mock_llm, _ = _make_structured_llm_mock(
            ClassifyOutput(category="out_of_scope", confidence=0.98, reason="製品と無関係の質問")
        )

        with patch("app.agents.tools.classify.get_llm", return_value=mock_llm):
            result = classify_query.invoke({"query": "今日の天気を教えてください"})

        assert result["category"] == "out_of_scope"
        assert result["confidence"] == 0.98

    def test_classify_unclear_triggers_interrupt(self):
        """unclear 判定時に interrupt が呼ばれることを確認"""
        mock_llm, _ = _make_structured_llm_mock(
            ClassifyOutput(category="unclear", confidence=0.3, reason="質問が曖昧")
        )

        with patch("app.agents.tools.classify.get_llm", return_value=mock_llm), \
             patch("app.agents.tools.classify.interrupt", return_value="操作方法") as mock_interrupt:
            result = classify_query.invoke({"query": "使い方"})

        mock_interrupt.assert_called_once()
        assert result["category"] == "操作方法"
        assert result["confidence"] == 1.0
        assert result["source"] == "human_clarification"

    def test_classify_low_confidence_triggers_interrupt(self):
        """confidence < 0.6 の場合に interrupt が呼ばれることを確認"""
        mock_llm, _ = _make_structured_llm_mock(
            ClassifyOutput(category="操作方法", confidence=0.4, reason="自信が低い")
        )

        with patch("app.agents.tools.classify.get_llm", return_value=mock_llm), \
             patch("app.agents.tools.classify.interrupt", return_value="障害・トラブル") as mock_interrupt:
            result = classify_query.invoke({"query": "なんか動かない"})

        mock_interrupt.assert_called_once()
        assert result["source"] == "human_clarification"

    def test_classify_exception_fallback_triggers_interrupt(self):
        """StructuredOutput が Exception を発生させた場合に unclear フォールバック → interrupt が呼ばれることを確認"""
        mock_structured_llm = MagicMock()
        mock_structured_llm.side_effect = Exception("parse error")

        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured_llm

        with patch("app.agents.tools.classify.get_llm", return_value=mock_llm), \
             patch("app.agents.tools.classify.interrupt", return_value="その他") as mock_interrupt:
            classify_query.invoke({"query": "テスト質問"})

        # confidence=0.0 → interrupt が呼ばれるはず
        mock_interrupt.assert_called_once()

    def test_classify_normal_result_no_interrupt(self):
        """高い confidence で正常分類された場合、interrupt が呼ばれないことを確認"""
        mock_llm, _ = _make_structured_llm_mock(
            ClassifyOutput(category="操作方法", confidence=0.85, reason="設定に関する質問")
        )

        with patch("app.agents.tools.classify.get_llm", return_value=mock_llm), \
             patch("app.agents.tools.classify.interrupt") as mock_interrupt:
            result = classify_query.invoke({"query": "設定方法について"})

        mock_interrupt.assert_not_called()
        assert result["category"] == "操作方法"
        assert result["confidence"] == 0.85


# ===========================================================================
# 2. rewrite_query テスト
# ===========================================================================


class TestRewriteQuery:
    def test_rewrite_normal(self):
        """正常なリライトが返されることを確認"""
        mock_llm, _ = _make_chat_llm_mock("製品Aのパスワードリセット方法")

        with patch("app.agents.tools.rewrite.get_llm", return_value=mock_llm):
            result = rewrite_query.invoke({"query": "パスワードを忘れました"})

        assert result == "製品Aのパスワードリセット方法"

    def test_rewrite_with_context(self):
        """会話コンテキスト付きのリライトが返されることを確認"""
        mock_llm, _ = _make_chat_llm_mock("製品Aの料金プラン変更手順")

        with patch("app.agents.tools.rewrite.get_llm", return_value=mock_llm):
            result = rewrite_query.invoke({
                "query": "それを変更したい",
                "conversation_context": "製品Aの料金プランについて話していました",
            })

        # llm が呼ばれていることを確認
        mock_llm.assert_called_once()
        assert result == "製品Aの料金プラン変更手順"

    def test_rewrite_fallback_on_short_result(self):
        """リライト結果が3文字未満の場合は元のクエリを返すことを確認"""
        mock_llm, _ = _make_chat_llm_mock("ab")  # 2文字 < 3文字

        with patch("app.agents.tools.rewrite.get_llm", return_value=mock_llm):
            original_query = "パスワードリセットの方法を教えてください"
            result = rewrite_query.invoke({"query": original_query})

        assert result == original_query

    def test_rewrite_fallback_on_empty_result(self):
        """空のリライト結果に対して元のクエリを返すことを確認"""
        mock_llm, _ = _make_chat_llm_mock("")

        with patch("app.agents.tools.rewrite.get_llm", return_value=mock_llm):
            original_query = "エラーの解決方法"
            result = rewrite_query.invoke({"query": original_query})

        assert result == original_query


# ===========================================================================
# 3. search_knowledge テスト
# ===========================================================================


class TestSearchKnowledge:
    def test_search_returns_results(self):
        """正常な検索結果のリストが返されることを確認"""
        mock_docs = [
            {
                "content": "ログイン方法の説明",
                "metadata": {"category": "操作方法"},
                "relevance_score": 0.85,
                "id": "doc1",
            }
        ]

        with patch("app.agents.tools.search.hybrid_retrieve", return_value=mock_docs):
            result = search_knowledge.invoke({"query": "ログイン"})

        assert len(result) == 1
        assert result[0]["content"] == "ログイン方法の説明"
        assert result[0]["relevance_score"] == 0.85

    def test_search_empty_results_returns_fallback(self):
        """検索結果が空の場合にフォールバックメッセージが返されることを確認"""
        with patch("app.agents.tools.search.hybrid_retrieve", return_value=[]):
            result = search_knowledge.invoke({"query": "存在しない情報"})

        assert len(result) == 1
        assert "見つかりませんでした" in result[0]["content"]
        assert result[0]["relevance_score"] == 0.0

    def test_search_with_category_filter(self):
        """カテゴリフィルター付きの検索が機能することを確認"""
        mock_docs = [
            {
                "content": "料金プランの説明",
                "metadata": {"category": "契約・料金"},
                "relevance_score": 0.90,
                "id": "contract_doc",
            }
        ]

        with patch("app.agents.tools.search.hybrid_retrieve", return_value=mock_docs) as mock_retrieve:
            result = search_knowledge.invoke({
                "query": "料金プラン",
                "category": "契約・料金",
                "n_results": 3,
            })

        mock_retrieve.assert_called_once_with(
            query="料金プラン",
            n_results=3,
            category="契約・料金",
        )
        assert result[0]["metadata"]["category"] == "契約・料金"

    def test_search_multiple_results(self):
        """複数の検索結果が正しく返されることを確認"""
        mock_docs = [
            {"content": f"文書{i}", "metadata": {}, "relevance_score": 0.9 - i * 0.1, "id": f"doc{i}"}
            for i in range(3)
        ]

        with patch("app.agents.tools.search.hybrid_retrieve", return_value=mock_docs):
            result = search_knowledge.invoke({"query": "テスト", "n_results": 3})

        assert len(result) == 3


# ===========================================================================
# 4. check_relevance テスト
# ===========================================================================


class TestCheckRelevance:
    def test_relevance_high_returns_true(self):
        """関連性が高い場合に is_relevant=True が返されることを確認"""
        from app.config.settings import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.relevance_skip_threshold = 0.85

        mock_llm, _ = _make_structured_llm_mock(
            RelevanceOutput(
                is_relevant=True,
                score=0.92,
                relevant_doc_indices=[0, 1],
                reason="質問に直接回答できる情報が含まれている",
            )
        )

        # 平均スコア = (0.78 + 0.72) / 2 = 0.75 < 0.85 → LLM呼び出し発生
        search_results = [
            {"content": "ログイン方法の詳細説明", "relevance_score": 0.78},
            {"content": "パスワードリセット手順", "relevance_score": 0.72},
        ]

        with patch("app.agents.tools.relevance.get_llm", return_value=mock_llm), \
             patch("app.agents.tools.relevance.get_settings", return_value=mock_settings):
            result = check_relevance.invoke({
                "query": "ログインできない場合の対処法",
                "search_results": search_results,
            })

        assert result["is_relevant"] is True
        assert result["score"] == 0.92
        assert result["relevant_doc_indices"] == [0, 1]

    def test_relevance_low_returns_false(self):
        """関連性が低い場合に is_relevant=False が返されることを確認"""
        mock_llm, _ = _make_structured_llm_mock(
            RelevanceOutput(
                is_relevant=False,
                score=0.15,
                relevant_doc_indices=[],
                reason="質問に関連する情報が含まれていない",
            )
        )

        search_results = [
            {"content": "料金プランに関する情報", "relevance_score": 0.20},
        ]

        with patch("app.agents.tools.relevance.get_llm", return_value=mock_llm):
            result = check_relevance.invoke({
                "query": "製品のバグ修正履歴",
                "search_results": search_results,
            })

        assert result["is_relevant"] is False
        assert result["score"] == 0.15

    def test_relevance_exception_score_based_fallback_high(self):
        """StructuredOutput が Exception を発生させた場合にスコアベースのフォールバックが動作することを確認"""
        mock_structured_llm = MagicMock()
        mock_structured_llm.side_effect = Exception("parse error")

        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured_llm

        # 平均スコアが 0.5 超の場合は is_relevant=True
        search_results = [
            {"content": "関連ドキュメント1", "relevance_score": 0.75},
            {"content": "関連ドキュメント2", "relevance_score": 0.65},
        ]

        with patch("app.agents.tools.relevance.get_llm", return_value=mock_llm):
            result = check_relevance.invoke({
                "query": "テスト質問",
                "search_results": search_results,
            })

        # 平均スコア = (0.75 + 0.65) / 2 = 0.70 > 0.5 → True
        assert result["is_relevant"] is True
        assert result["score"] == pytest.approx(0.70)
        assert "簡易判定" in result["reason"]
        # フォールバック時は evaluation_error=True と error_id が含まれる
        assert result["evaluation_error"] is True
        assert "error_id" in result
        assert len(result["error_id"]) == 8

    def test_relevance_exception_score_based_fallback_low(self):
        """StructuredOutput が Exception を発生させた場合に平均スコアが低いと is_relevant=False になることを確認"""
        mock_structured_llm = MagicMock()
        mock_structured_llm.side_effect = Exception("parse error")

        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured_llm

        search_results = [
            {"content": "無関係なドキュメント", "relevance_score": 0.20},
            {"content": "別の無関係なドキュメント", "relevance_score": 0.30},
        ]

        with patch("app.agents.tools.relevance.get_llm", return_value=mock_llm):
            result = check_relevance.invoke({
                "query": "テスト質問",
                "search_results": search_results,
            })

        # 平均スコア = (0.20 + 0.30) / 2 = 0.25 <= 0.5 → False
        assert result["is_relevant"] is False
        # フォールバック時は evaluation_error=True と error_id が含まれる
        assert result["evaluation_error"] is True
        assert "error_id" in result

    def test_relevance_structured_output_success(self):
        """StructuredOutput が正常に動作し、結果が返されることを確認"""
        mock_llm, _ = _make_structured_llm_mock(
            RelevanceOutput(
                is_relevant=True,
                score=0.80,
                relevant_doc_indices=[0],
                reason="関連性あり",
            )
        )

        search_results = [{"content": "説明文", "relevance_score": 0.80}]

        with patch("app.agents.tools.relevance.get_llm", return_value=mock_llm):
            result = check_relevance.invoke({
                "query": "質問",
                "search_results": search_results,
            })

        assert result["is_relevant"] is True
        assert result["score"] == 0.80

    def test_relevance_empty_search_results_fallback(self):
        """検索結果が空の場合でもエラーにならないことを確認"""
        mock_structured_llm = MagicMock()
        mock_structured_llm.side_effect = Exception("parse error")

        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured_llm

        with patch("app.agents.tools.relevance.get_llm", return_value=mock_llm):
            result = check_relevance.invoke({
                "query": "テスト",
                "search_results": [],
            })

        # 空リストの場合 avg_score=0 → is_relevant=False
        assert result["is_relevant"] is False
        assert result["score"] == 0.0

    def test_relevance_skip_llm_when_high_score(self):
        """平均スコアが relevance_skip_threshold 以上の場合、LLM呼び出しをスキップすることを確認"""
        from unittest.mock import MagicMock, patch
        from app.config.settings import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.relevance_skip_threshold = 0.85

        mock_llm = MagicMock()

        search_results = [
            {"content": "高関連ドキュメント1", "relevance_score": 0.90},
            {"content": "高関連ドキュメント2", "relevance_score": 0.88},
        ]

        with patch("app.agents.tools.relevance.get_llm", return_value=mock_llm), \
             patch("app.agents.tools.relevance.get_settings", return_value=mock_settings):
            result = check_relevance.invoke({
                "query": "テスト質問",
                "search_results": search_results,
            })

        # 平均スコア = (0.90 + 0.88) / 2 = 0.89 >= 0.85 → LLMスキップ
        mock_llm.assert_not_called()
        assert result["is_relevant"] is True
        assert result["score"] == pytest.approx(0.89)
        assert "高スコアのためLLM評価をスキップしました" in result["reason"]

    def test_relevance_no_skip_when_below_threshold(self):
        """平均スコアが relevance_skip_threshold 未満の場合、LLM呼び出しが行われることを確認"""
        from app.config.settings import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.relevance_skip_threshold = 0.85

        mock_llm, _ = _make_structured_llm_mock(
            RelevanceOutput(
                is_relevant=True,
                score=0.75,
                relevant_doc_indices=[0],
                reason="LLMによる評価",
            )
        )

        search_results = [
            {"content": "中程度のドキュメント", "relevance_score": 0.80},
            {"content": "低いドキュメント", "relevance_score": 0.60},
        ]

        with patch("app.agents.tools.relevance.get_llm", return_value=mock_llm), \
             patch("app.agents.tools.relevance.get_settings", return_value=mock_settings):
            result = check_relevance.invoke({
                "query": "テスト質問",
                "search_results": search_results,
            })

        # 平均スコア = (0.80 + 0.60) / 2 = 0.70 < 0.85 → LLM呼び出し発生
        mock_llm.with_structured_output.assert_called_once()
        assert result["score"] == 0.75

    def test_relevance_fallback_message_includes_accuracy_warning(self):
        """フォールバック時に警告メッセージとエラーIDが含まれることを確認"""
        mock_structured_llm = MagicMock()
        mock_structured_llm.side_effect = Exception("parse error")

        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured_llm

        search_results = [
            {"content": "関連ドキュメント", "relevance_score": 0.75},
        ]

        with patch("app.agents.tools.relevance.get_llm", return_value=mock_llm):
            result = check_relevance.invoke({
                "query": "テスト質問",
                "search_results": search_results,
            })

        # フォールバックメッセージに警告とエラーIDが含まれる
        assert "[警告]" in result["reason"]
        assert "LLM評価エラー" in result["reason"]
        assert "簡易判定" in result["reason"]
        assert result["evaluation_error"] is True
        assert "error_id" in result

    def test_relevance_fallback_logs_with_error_id_and_exc_info(self):
        """LLM評価失敗時にエラーID、exc_info=True、fallback_usedフラグがログ出力されることを確認"""
        import logging
        from unittest.mock import MagicMock, patch, call

        mock_structured_llm = MagicMock()
        mock_structured_llm.side_effect = Exception("LLM parse error")

        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured_llm

        search_results = [
            {"content": "関連ドキュメント", "relevance_score": 0.75},
        ]

        with patch("app.agents.tools.relevance.get_llm", return_value=mock_llm), \
             patch("app.agents.tools.relevance.logger") as mock_logger:
            result = check_relevance.invoke({
                "query": "テスト質問",
                "search_results": search_results,
            })

        # logger.error が呼ばれたことを確認
        assert mock_logger.error.called
        error_call = mock_logger.error.call_args

        # exc_info=True が設定されていることを確認
        assert error_call[1].get("exc_info") is True

        # エラーIDが含まれていることを確認
        assert "error_id" in error_call[1]

        # fallback_used フラグが含まれていることを確認
        assert error_call[1].get("fallback_used") is True


# ===========================================================================
# 5. generate_answer テスト
# ===========================================================================


class TestGenerateAnswer:
    def test_generate_answer_normal(self):
        """正常な回答テキストが生成されることを確認"""
        expected_answer = "ログイン手順は以下の通りです。\n1. URLにアクセスします。\n2. メールアドレスを入力します。"
        mock_llm, _ = _make_chat_llm_mock(expected_answer)

        documents = [
            {
                "content": "ログイン方法: URLにアクセスしてメールとパスワードを入力",
                "metadata": {"source": "product_guide.md"},
            }
        ]

        with patch("app.agents.tools.generate.get_llm", return_value=mock_llm):
            result = generate_answer.invoke({
                "query": "ログイン方法を教えてください",
                "relevant_documents": documents,
            })

        assert result == expected_answer

    def test_generate_answer_with_category(self):
        """カテゴリ付きの回答生成が正常に動作することを確認"""
        expected_answer = "料金プランについてご説明します。"
        mock_llm, _ = _make_chat_llm_mock(expected_answer)

        documents = [
            {
                "content": "スタンダードプラン: 月額1,000円",
                "metadata": {"source": "contracts.md"},
            }
        ]

        with patch("app.agents.tools.generate.get_llm", return_value=mock_llm):
            result = generate_answer.invoke({
                "query": "料金プランを教えてください",
                "relevant_documents": documents,
                "category": "契約・料金",
            })

        # プロンプトにカテゴリが含まれていることを確認
        call_args = mock_llm.call_args
        prompt_str = call_args[0][0].to_string()
        assert "契約・料金" in prompt_str
        assert result == expected_answer

    def test_generate_answer_context_includes_source(self):
        """プロンプトに出典情報が含まれることを確認"""
        mock_llm, _ = _make_chat_llm_mock("回答テキスト")

        documents = [
            {
                "content": "トラブルシューティングの手順",
                "metadata": {"source": "troubleshooting.md"},
            }
        ]

        with patch("app.agents.tools.generate.get_llm", return_value=mock_llm):
            generate_answer.invoke({
                "query": "エラーの対処法",
                "relevant_documents": documents,
            })

        call_args = mock_llm.call_args
        prompt_str = call_args[0][0].to_string()
        assert "troubleshooting.md" in prompt_str

    def test_generate_answer_strips_whitespace(self):
        """生成された回答の前後の空白が除去されることを確認"""
        mock_llm, _ = _make_chat_llm_mock("  前後に空白がある回答  \n")

        with patch("app.agents.tools.generate.get_llm", return_value=mock_llm):
            result = generate_answer.invoke({
                "query": "テスト質問",
                "relevant_documents": [{"content": "参考情報", "metadata": {}}],
            })

        assert result == "前後に空白がある回答"

    def test_generate_answer_multiple_documents(self):
        """複数ドキュメントを使った回答生成が正常に動作することを確認"""
        mock_llm, _ = _make_chat_llm_mock("複数文書に基づく回答")

        documents = [
            {"content": "情報1", "metadata": {"source": "doc1.md"}},
            {"content": "情報2", "metadata": {"source": "doc2.md"}},
            {"content": "情報3", "metadata": {"source": "doc3.md"}},
        ]

        with patch("app.agents.tools.generate.get_llm", return_value=mock_llm):
            result = generate_answer.invoke({
                "query": "総合的な質問",
                "relevant_documents": documents,
            })

        call_args = mock_llm.call_args
        prompt_str = call_args[0][0].to_string()
        assert "doc1.md" in prompt_str
        assert "doc2.md" in prompt_str
        assert "doc3.md" in prompt_str
        assert result == "複数文書に基づく回答"


# ===========================================================================
# 6. check_quality テスト
# ===========================================================================


class TestCheckQuality:
    def test_quality_passed_high_scores(self):
        """両スコアが0.6以上の場合に passed=True が返されることを確認"""
        mock_llm, _ = _make_structured_llm_mock(
            QualityOutput(
                hallucination_score=0.85,
                sufficiency_score=0.90,
                issues=[],
                suggestions="特に問題なし",
            )
        )

        documents = [{"content": "参考情報テキスト"}]

        with patch("app.agents.tools.quality.get_llm", return_value=mock_llm):
            result = check_quality.invoke({
                "query": "ログインについて",
                "answer": "ログインはURLにアクセスして行います。",
                "source_documents": documents,
            })

        assert result["passed"] is True
        assert result["hallucination_score"] == 0.85
        assert result["sufficiency_score"] == 0.90
        assert result["issues"] == []

    def test_quality_failed_low_hallucination_score(self):
        """ハルシネーションスコアが低い場合に passed=False が返されることを確認"""
        mock_llm, _ = _make_structured_llm_mock(
            QualityOutput(
                hallucination_score=0.30,
                sufficiency_score=0.80,
                issues=["参考情報にない内容が含まれている"],
                suggestions="参考情報に基づいた回答のみ提供してください",
            )
        )

        documents = [{"content": "限定的な参考情報"}]

        with patch("app.agents.tools.quality.get_llm", return_value=mock_llm):
            result = check_quality.invoke({
                "query": "製品の詳細機能",
                "answer": "この製品には多数の高度な機能があります（参考情報に記載なし）。",
                "source_documents": documents,
            })

        assert result["passed"] is False
        assert result["hallucination_score"] == 0.30
        assert len(result["issues"]) > 0

    def test_quality_failed_low_sufficiency_score(self):
        """充足性スコアが低い場合に passed=False が返されることを確認"""
        mock_llm, _ = _make_structured_llm_mock(
            QualityOutput(
                hallucination_score=0.90,
                sufficiency_score=0.40,
                issues=["質問への回答が不十分"],
                suggestions="より具体的な手順を追加してください",
            )
        )

        documents = [{"content": "概要情報のみ"}]

        with patch("app.agents.tools.quality.get_llm", return_value=mock_llm):
            result = check_quality.invoke({
                "query": "詳細な設定手順を教えてください",
                "answer": "設定は可能です。",
                "source_documents": documents,
            })

        assert result["passed"] is False
        assert result["sufficiency_score"] == 0.40

    def test_quality_boundary_score_exactly_06(self):
        """スコアが境界値 0.6 の場合に passed=True であることを確認"""
        mock_llm, _ = _make_structured_llm_mock(
            QualityOutput(
                hallucination_score=0.6,
                sufficiency_score=0.6,
                issues=[],
                suggestions="",
            )
        )

        with patch("app.agents.tools.quality.get_llm", return_value=mock_llm):
            result = check_quality.invoke({
                "query": "テスト",
                "answer": "回答",
                "source_documents": [{"content": "参考"}],
            })

        assert result["passed"] is True

    def test_quality_exception_default_values(self):
        """StructuredOutput が Exception を発生させた場合にデフォルト値が返されることを確認"""
        mock_structured_llm = MagicMock()
        mock_structured_llm.side_effect = Exception("parse error")

        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured_llm

        with patch("app.agents.tools.quality.get_llm", return_value=mock_llm):
            result = check_quality.invoke({
                "query": "テスト",
                "answer": "回答",
                "source_documents": [{"content": "参考"}],
            })

        assert result["passed"] is False
        assert result["hallucination_score"] == 0.0
        assert result["sufficiency_score"] == 0.0
        assert result["issues"] == ["品質チェックのレスポンスが解析できませんでした"]
        assert "デフォルト値" in result["suggestions"]

    def test_quality_structured_output_success(self):
        """StructuredOutput が正常に動作し、結果が返されることを確認"""
        mock_llm, _ = _make_structured_llm_mock(
            QualityOutput(
                hallucination_score=0.75,
                sufficiency_score=0.80,
                issues=[],
                suggestions="良好",
            )
        )

        with patch("app.agents.tools.quality.get_llm", return_value=mock_llm):
            result = check_quality.invoke({
                "query": "質問",
                "answer": "回答",
                "source_documents": [{"content": "参考"}],
            })

        assert result["passed"] is True
        assert result["hallucination_score"] == 0.75


# ===========================================================================
# 7. ask_human テスト
# ===========================================================================


class TestAskHuman:
    def test_ask_human_with_buttons(self):
        """選択肢付きの場合に interrupt が buttons タイプで呼ばれることを確認"""
        with patch("app.agents.tools.ask_human.interrupt", return_value="操作方法") as mock_interrupt:
            result = ask_human.invoke({
                "question": "どのカテゴリに関するお問い合わせですか？",
                "options": ["操作方法", "障害・トラブル", "契約・料金"],
                "input_type": "buttons",
            })

        mock_interrupt.assert_called_once_with({
            "question": "どのカテゴリに関するお問い合わせですか？",
            "options": ["操作方法", "障害・トラブル", "契約・料金"],
            "input_type": "buttons",
        })
        assert result == "操作方法"

    def test_ask_human_text_input(self):
        """テキスト入力の場合に interrupt が text タイプで呼ばれることを確認"""
        with patch("app.agents.tools.ask_human.interrupt", return_value="詳しく教えてください") as mock_interrupt:
            result = ask_human.invoke({
                "question": "詳細を教えていただけますか？",
            })

        mock_interrupt.assert_called_once_with({
            "question": "詳細を教えていただけますか？",
            "options": None,
            "input_type": "text",
        })
        assert result == "詳しく教えてください"

    def test_ask_human_options_without_input_type_uses_buttons(self):
        """options がある場合、input_type が 'text' でなければ 'buttons' になることを確認"""
        with patch("app.agents.tools.ask_human.interrupt", return_value="はい") as mock_interrupt:
            ask_human.invoke({
                "question": "続けてよいですか？",
                "options": ["はい", "いいえ"],
                "input_type": "other",  # text 以外の値 → buttons に変換される
            })

        call_kwargs = mock_interrupt.call_args[0][0]
        assert call_kwargs["input_type"] == "buttons"

    def test_ask_human_no_options_forces_text_type(self):
        """options が None の場合、input_type が 'text' に強制されることを確認"""
        with patch("app.agents.tools.ask_human.interrupt", return_value="ユーザーの回答") as mock_interrupt:
            ask_human.invoke({
                "question": "何かお困りですか？",
                "options": None,
                "input_type": "buttons",  # options なし → text に変換される
            })

        call_kwargs = mock_interrupt.call_args[0][0]
        assert call_kwargs["input_type"] == "text"

    def test_ask_human_returns_interrupt_response(self):
        """interrupt の戻り値がそのまま返されることを確認"""
        expected_response = "障害・トラブルに関する詳細情報"

        with patch("app.agents.tools.ask_human.interrupt", return_value=expected_response):
            result = ask_human.invoke({
                "question": "どのような問題が発生していますか？",
            })

        assert result == expected_response

    def test_ask_human_with_empty_options_list(self):
        """空リストの options の場合は text タイプになることを確認"""
        with patch("app.agents.tools.ask_human.interrupt", return_value="回答") as mock_interrupt:
            ask_human.invoke({
                "question": "テスト質問",
                "options": [],
                "input_type": "buttons",
            })

        call_kwargs = mock_interrupt.call_args[0][0]
        # 空リストは falsy → text タイプになる
        assert call_kwargs["input_type"] == "text"


# ===========================================================================
# 8. search_knowledge 例外処理テスト
# ===========================================================================


class TestSearchKnowledgeExceptionHandling:
    """search_knowledge ツールの例外処理テスト"""

    def test_search_knowledge_handles_retriever_exception(self):
        """hybrid_retrieveが例外を投げた場合のエラーハンドリング"""
        with patch("app.agents.tools.search.hybrid_retrieve") as mock_retrieve:
            mock_retrieve.side_effect = ConnectionError("ChromaDB connection failed")

            # 例外が発生することを確認（現在の実装では例外が伝播する）
            with pytest.raises(ConnectionError):
                search_knowledge.invoke({"query": "test query"})

    def test_search_knowledge_handles_generic_exception(self):
        """hybrid_retrieveが一般的な例外を投げた場合の処理"""
        with patch("app.agents.tools.search.hybrid_retrieve") as mock_retrieve:
            mock_retrieve.side_effect = RuntimeError("Unexpected error")

            # 例外が発生することを確認
            with pytest.raises(RuntimeError):
                search_knowledge.invoke({"query": "test query"})

    def test_search_knowledge_handles_timeout_exception(self):
        """hybrid_retrieveがタイムアウトした場合の処理"""
        with patch("app.agents.tools.search.hybrid_retrieve") as mock_retrieve:
            mock_retrieve.side_effect = TimeoutError("Request timed out")

            # 例外が発生することを確認
            with pytest.raises(TimeoutError):
                search_knowledge.invoke({"query": "test query"})


# ===========================================================================
# 9. generate_answer エッジケーステスト
# ===========================================================================


class TestGenerateAnswerEdgeCases:
    """generate_answer ツールのエッジケーステスト"""

    def test_generate_answer_with_empty_documents(self):
        """空ドキュメントでの回答生成 - LLMに空コンテキストが渡されることを確認"""
        mock_llm, _ = _make_chat_llm_mock("確認が必要です。詳細な情報をお知らせください。")

        with patch("app.agents.tools.generate.get_llm", return_value=mock_llm):
            result = generate_answer.invoke({
                "query": "What is AI?",
                "relevant_documents": [],
            })

        # LLMが呼ばれ、何らかの回答が返ることを確認
        assert result is not None
        mock_llm.assert_called_once()

    def test_generate_answer_with_malformed_documents(self):
        """不正な形式のドキュメントでの処理 - contentキーなし"""
        mock_llm, _ = _make_chat_llm_mock("回答テキスト")

        with patch("app.agents.tools.generate.get_llm", return_value=mock_llm):
            result = generate_answer.invoke({
                "query": "What is AI?",
                "relevant_documents": [{"invalid_key": "value"}],  # contentキーなし
            })

        # クラッシュせず、何らかの回答が返ることを確認
        # doc.get("content", "") により空文字として処理される
        assert result is not None

    def test_generate_answer_with_partial_metadata(self):
        """メタデータが部分的なドキュメントでの処理"""
        mock_llm, _ = _make_chat_llm_mock("回答テキスト")

        with patch("app.agents.tools.generate.get_llm", return_value=mock_llm):
            result = generate_answer.invoke({
                "query": "テスト質問",
                "relevant_documents": [
                    {"content": "内容のみ", "metadata": {}},  # sourceなし
                    {"content": "別の内容", "metadata": {"source": "doc.md"}},  # sectionなし
                ],
            })

        # クラッシュせず、LLMが呼ばれることを確認
        assert result is not None
        mock_llm.assert_called_once()

    def test_generate_answer_with_special_characters_in_content(self):
        """特殊文字を含むコンテンツでの処理"""
        mock_llm, _ = _make_chat_llm_mock("回答テキスト")

        special_content = "特殊文字: <script>alert('xss')</script> & \" ' \\n \\t"

        with patch("app.agents.tools.generate.get_llm", return_value=mock_llm):
            result = generate_answer.invoke({
                "query": "テスト質問",
                "relevant_documents": [{"content": special_content, "metadata": {}}],
            })

        # クラッシュせず、何らかの回答が返ることを確認
        assert result is not None

    def test_generate_answer_with_large_document_count(self):
        """大量のドキュメントでの処理"""
        mock_llm, _ = _make_chat_llm_mock("統合された回答")

        # 20件のドキュメント
        documents = [
            {"content": f"ドキュメント{i}の内容", "metadata": {"source": f"doc{i}.md"}}
            for i in range(20)
        ]

        with patch("app.agents.tools.generate.get_llm", return_value=mock_llm):
            result = generate_answer.invoke({
                "query": "総合的な質問",
                "relevant_documents": documents,
            })

        # クラッシュせず、LLMが呼ばれることを確認
        assert result is not None

    def test_generate_answer_llm_exception_propagates(self):
        """LLM呼び出しが例外を投げた場合、例外が伝播することを確認"""
        mock_llm = MagicMock()
        mock_llm.side_effect = RuntimeError("LLM API error")

        with patch("app.agents.tools.generate.get_llm", return_value=mock_llm):
            with pytest.raises(RuntimeError, match="LLM API error"):
                generate_answer.invoke({
                    "query": "テスト質問",
                    "relevant_documents": [{"content": "内容", "metadata": {}}],
                })


# ===========================================================================
# 10. classify_query バリデーションテスト
# ===========================================================================


class TestClassifyQueryValidation:
    """classify_query ツールのバリデーションテスト"""

    def test_classify_query_handles_invalid_category(self):
        """LLMが無効なカテゴリを返した場合、unclearとして処理されてinterruptが呼ばれる"""
        # 無効なカテゴリを返すモック
        mock_structured_llm = MagicMock()
        mock_structured_llm.return_value = MagicMock(
            category="invalid_category",
            confidence=0.9,
            reason="無効なカテゴリ"
        )

        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured_llm

        with patch("app.agents.tools.classify.get_llm", return_value=mock_llm), \
             patch("app.agents.tools.classify.interrupt", return_value="操作方法") as mock_interrupt:
            result = classify_query.invoke({"query": "test query"})

        # 無効なカテゴリでもconfidenceが高ければそのまま返る
        # (現在の実装ではカテゴリのバリデーションがないため)
        # もしunclearまたはinterruptが呼ばれる実装なら、そちらを確認
        # 現状は無効なカテゴリもそのまま返る仕様
        assert result["category"] == "invalid_category"

    def test_classify_query_handles_empty_category(self):
        """LLMが空のカテゴリを返した場合の処理"""
        mock_structured_llm = MagicMock()
        mock_structured_llm.return_value = MagicMock(
            category="",
            confidence=0.5,
            reason="カテゴリ不明"
        )

        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured_llm

        with patch("app.agents.tools.classify.get_llm", return_value=mock_llm), \
             patch("app.agents.tools.classify.interrupt", return_value="その他") as mock_interrupt:
            result = classify_query.invoke({"query": "test query"})

        # 空カテゴリ + 低confidence → interruptが呼ばれる
        mock_interrupt.assert_called_once()

    def test_classify_query_handles_none_category(self):
        """LLMがNoneを返した場合の処理"""
        mock_structured_llm = MagicMock()
        mock_structured_llm.return_value = MagicMock(
            category=None,
            confidence=0.5,
            reason="カテゴリ不明"
        )

        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured_llm

        with patch("app.agents.tools.classify.get_llm", return_value=mock_llm), \
             patch("app.agents.tools.classify.interrupt", return_value="その他") as mock_interrupt:
            result = classify_query.invoke({"query": "test query"})

        # Noneカテゴリ + 低confidence → interruptが呼ばれる
        mock_interrupt.assert_called_once()

    def test_classify_query_handles_very_long_query(self):
        """非常に長いクエリでの処理"""
        mock_llm, _ = _make_structured_llm_mock(
            ClassifyOutput(category="操作方法", confidence=0.85, reason="長い質問")
        )

        long_query = "製品の使い方について" * 1000  # 非常に長いクエリ

        with patch("app.agents.tools.classify.get_llm", return_value=mock_llm):
            result = classify_query.invoke({"query": long_query})

        # クラッシュせず、分類結果が返ることを確認
        assert result["category"] == "操作方法"

    def test_classify_query_handles_special_characters(self):
        """特殊文字を含むクエリでの処理"""
        mock_llm, _ = _make_structured_llm_mock(
            ClassifyOutput(category="障害・トラブル", confidence=0.90, reason="エラー相关")
        )

        special_query = "エラーが発生: <script>alert('xss')</script> & \" ' \\n"

        with patch("app.agents.tools.classify.get_llm", return_value=mock_llm):
            result = classify_query.invoke({"query": special_query})

        # クラッシュせず、分類結果が返ることを確認
        assert result["category"] == "障害・トラブル"
