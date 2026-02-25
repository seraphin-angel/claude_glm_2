"""Multi-Query / HyDE 検索統合のテスト

テスト方針:
- retrieve_with_multi_query と retrieve_with_hyde のテスト
- retrieve_with_strategy の戦略選択テスト
- モックを使用して外部依存を排除
"""

from unittest.mock import MagicMock, patch

import pytest

from app.config.settings import Settings


class TestRetrieveWithMultiQuery:
    """retrieve_with_multi_query 関数のテスト"""

    def test_returns_merged_results(self):
        """複数クエリの結果がマージされて返ることを確認"""
        from app.rag import retriever

        # rewrite_query_multi のモック
        mock_queries = ["クエリ1", "クエリ2", "クエリ3"]

        # retrieve_documents のモック結果
        mock_results_1 = [
            {"id": "doc1", "content": "内容1", "metadata": {}, "relevance_score": 0.9}
        ]
        mock_results_2 = [
            {"id": "doc2", "content": "内容2", "metadata": {}, "relevance_score": 0.8}
        ]
        mock_results_3 = [
            {"id": "doc1", "content": "内容1", "metadata": {}, "relevance_score": 0.85},
            {"id": "doc3", "content": "内容3", "metadata": {}, "relevance_score": 0.7}
        ]

        with patch("app.rag.retriever.rewrite_query_multi", return_value=mock_queries), \
             patch("app.rag.retriever.retrieve_documents") as mock_retrieve:
            mock_retrieve.side_effect = [mock_results_1, mock_results_2, mock_results_3]

            result = retriever.retrieve_with_multi_query("テストクエリ", n_results=5)

        # RRFでマージされた結果が返る
        assert len(result) > 0
        # doc1 が複数回登場しているため高いスコアを持つはず
        assert result[0]["id"] == "doc1"

    def test_respects_n_results(self):
        """n_results で指定された件数が守られることを確認"""
        from app.rag import retriever

        mock_queries = ["クエリ1", "クエリ2"]
        mock_results = [
            {"id": f"doc{i}", "content": f"内容{i}", "metadata": {}, "relevance_score": 0.9 - i * 0.1}
            for i in range(10)
        ]

        with patch("app.rag.retriever.rewrite_query_multi", return_value=mock_queries), \
             patch("app.rag.retriever.retrieve_documents", return_value=mock_results[:5]):
            result = retriever.retrieve_with_multi_query("テスト", n_results=3)

        assert len(result) <= 3

    def test_uses_settings_for_query_count(self):
        """設定の multi_query_count が使用されることを確認"""
        from app.rag import retriever

        mock_queries = ["クエリ1", "クエリ2", "クエリ3", "クエリ4"]

        with patch("app.rag.retriever.rewrite_query_multi", return_value=mock_queries) as mock_multi, \
             patch("app.rag.retriever.retrieve_documents", return_value=[]), \
             patch("app.rag.retriever.get_settings") as mock_settings:
            mock_settings.return_value = Settings(multi_query_count=4)

            retriever.retrieve_with_multi_query("テスト")

            # rewrite_query_multi が設定値で呼ばれることを確認
            mock_multi.assert_called_once_with("テスト", n=4)


class TestRetrieveWithHyde:
    """retrieve_with_hyde 関数のテスト"""

    def test_uses_hypothetical_answer_for_search(self):
        """仮説回答が検索に使用されることを確認"""
        from app.rag import retriever

        hypothetical_answer = "これは仮説の回答文書です。詳細な情報が含まれています。"
        mock_results = [
            {"id": "doc1", "content": "関連文書", "metadata": {}, "relevance_score": 0.9}
        ]

        with patch("app.rag.retriever.rewrite_query_hyde", return_value=hypothetical_answer) as mock_hyde, \
             patch("app.rag.retriever.retrieve_documents", return_value=mock_results) as mock_retrieve:
            result = retriever.retrieve_with_hyde("質問", n_results=5)

        # HyDE が呼ばれることを確認
        mock_hyde.assert_called_once_with("質問")
        # retrieve_documents が仮説回答で呼ばれることを確認
        mock_retrieve.assert_called_once_with(query=hypothetical_answer, n_results=5, category=None)
        assert result == mock_results

    def test_passes_category_filter(self):
        """カテゴリフィルタが渡されることを確認"""
        from app.rag import retriever

        with patch("app.rag.retriever.rewrite_query_hyde", return_value="仮説回答"), \
             patch("app.rag.retriever.retrieve_documents", return_value=[]) as mock_retrieve:
            retriever.retrieve_with_hyde("質問", n_results=5, category="操作方法")

        mock_retrieve.assert_called_once_with(
            query="仮説回答",
            n_results=5,
            category="操作方法"
        )


class TestRetrieveWithStrategy:
    """retrieve_with_strategy 関数のテスト"""

    def test_standard_strategy(self):
        """standard 戦略が通常の retrieve_documents を使用することを確認"""
        from app.rag import retriever

        mock_results = [{"id": "doc1", "content": "内容", "metadata": {}, "relevance_score": 0.9}]

        with patch("app.rag.retriever.retrieve_documents", return_value=mock_results) as mock_retrieve, \
             patch("app.rag.retriever.get_settings") as mock_settings:
            mock_settings.return_value = Settings(retrieval_strategy="standard")

            result = retriever.retrieve_with_strategy("質問", n_results=5)

        mock_retrieve.assert_called_once_with(query="質問", n_results=5, category=None)
        assert result == mock_results

    def test_multi_query_strategy(self):
        """multi_query 戦略が retrieve_with_multi_query を使用することを確認"""
        from app.rag import retriever

        mock_results = [{"id": "doc1", "content": "内容", "metadata": {}, "relevance_score": 0.9}]

        with patch("app.rag.retriever.retrieve_with_multi_query", return_value=mock_results) as mock_multi, \
             patch("app.rag.retriever.get_settings") as mock_settings:
            mock_settings.return_value = Settings(retrieval_strategy="multi_query")

            result = retriever.retrieve_with_strategy("質問", n_results=5, category="カテゴリ")

        mock_multi.assert_called_once_with(query="質問", n_results=5, category="カテゴリ")
        assert result == mock_results

    def test_hyde_strategy(self):
        """hyde 戦略が retrieve_with_hyde を使用することを確認"""
        from app.rag import retriever

        mock_results = [{"id": "doc1", "content": "内容", "metadata": {}, "relevance_score": 0.9}]

        with patch("app.rag.retriever.retrieve_with_hyde", return_value=mock_results) as mock_hyde, \
             patch("app.rag.retriever.get_settings") as mock_settings:
            mock_settings.return_value = Settings(retrieval_strategy="hyde")

            result = retriever.retrieve_with_strategy("質問", n_results=5)

        mock_hyde.assert_called_once_with(query="質問", n_results=5, category=None)
        assert result == mock_results

    def test_hybrid_strategy(self):
        """hybrid 戦略が multi_query を使用することを確認"""
        from app.rag import retriever

        mock_results = [{"id": "doc1", "content": "内容", "metadata": {}, "relevance_score": 0.9}]

        with patch("app.rag.retriever.retrieve_with_multi_query", return_value=mock_results) as mock_multi, \
             patch("app.rag.retriever.get_settings") as mock_settings:
            mock_settings.return_value = Settings(retrieval_strategy="hybrid")

            result = retriever.retrieve_with_strategy("質問", n_results=5)

        mock_multi.assert_called_once()
        assert result == mock_results

    def test_explicit_strategy_overrides_settings(self):
        """明示的な戦略指定が設定をオーバーライドすることを確認"""
        from app.rag import retriever

        mock_results = [{"id": "doc1", "content": "内容", "metadata": {}, "relevance_score": 0.9}]

        with patch("app.rag.retriever.retrieve_with_hyde", return_value=mock_results) as mock_hyde, \
             patch("app.rag.retriever.get_settings") as mock_settings:
            mock_settings.return_value = Settings(retrieval_strategy="standard")

            result = retriever.retrieve_with_strategy("質問", n_results=5, strategy="hyde")

        mock_hyde.assert_called_once()
        assert result == mock_results

    def test_invalid_strategy_falls_back_to_standard(self):
        """無効な戦略値は standard にフォールバックすることを確認"""
        from app.rag import retriever

        mock_results = [{"id": "doc1", "content": "内容", "metadata": {}, "relevance_score": 0.9}]

        with patch("app.rag.retriever.retrieve_documents", return_value=mock_results) as mock_retrieve, \
             patch("app.rag.retriever.get_settings") as mock_settings:
            mock_settings.return_value = Settings(retrieval_strategy="invalid_strategy")

            result = retriever.retrieve_with_strategy("質問", n_results=5)

        mock_retrieve.assert_called_once()
        assert result == mock_results
