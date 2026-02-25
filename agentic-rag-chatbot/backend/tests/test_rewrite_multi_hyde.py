"""Multi-Query / HyDE 機能のユニットテスト

テスト方針:
- LLM呼び出し（get_llm）は全て unittest.mock.patch でモック
- 各関数の入出力を検証
- プロンプト定数をモックしてチェーンのinvokeを制御
"""

from unittest.mock import MagicMock, patch

import pytest

from app.config.settings import Settings


class TestRewriteQueryMulti:
    """rewrite_query_multi 関数のテスト"""

    def test_returns_list_of_n_queries(self):
        """n個のクエリバリエーションを返すことを確認"""
        from app.rag import rewrite

        mock_response = MagicMock()
        mock_response.content = """1. 商品の返品方法を教えてください
2. 返品の手続きについて知りたい
3. 購入した商品を返すにはどうすればいいですか"""

        # モックプロンプトを作成
        mock_prompt = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = mock_response
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        with patch.object(rewrite, "_MULTI_QUERY_PROMPT", mock_prompt), \
             patch("app.rag.rewrite.get_llm"):
            result = rewrite.rewrite_query_multi("返品方法は？", n=3)

        assert len(result) == 3
        assert "返品" in result[0] or "返品" in result[1] or "返品" in result[2]

    def test_includes_original_query(self):
        """元のクエリが結果に含まれることを確認"""
        from app.rag import rewrite

        original_query = "返品方法は？"
        mock_response = MagicMock()
        mock_response.content = f"""1. {original_query}
2. 返品の手続きについて
3. 商品を返す方法"""

        mock_prompt = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = mock_response
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        with patch.object(rewrite, "_MULTI_QUERY_PROMPT", mock_prompt), \
             patch("app.rag.rewrite.get_llm"):
            result = rewrite.rewrite_query_multi(original_query, n=3)

        assert original_query in result

    def test_custom_n_value(self):
        """カスタムn値で動作することを確認"""
        from app.rag import rewrite

        mock_response = MagicMock()
        mock_response.content = """1. クエリ1
2. クエリ2
3. クエリ3
4. クエリ4
5. クエリ5"""

        mock_prompt = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = mock_response
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        with patch.object(rewrite, "_MULTI_QUERY_PROMPT", mock_prompt), \
             patch("app.rag.rewrite.get_llm"):
            result = rewrite.rewrite_query_multi("テスト", n=5)

        assert len(result) == 5

    def test_fallback_on_empty_response(self):
        """空のレスポンスの場合、元のクエリのみを返すことを確認"""
        from app.rag import rewrite

        mock_response = MagicMock()
        mock_response.content = ""

        mock_prompt = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = mock_response
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        with patch.object(rewrite, "_MULTI_QUERY_PROMPT", mock_prompt), \
             patch("app.rag.rewrite.get_llm"):
            result = rewrite.rewrite_query_multi("テストクエリ", n=3)

        assert result == ["テストクエリ"]

    def test_fallback_on_exception(self):
        """例外発生時は元のクエリのみを返すことを確認"""
        from app.rag import rewrite

        mock_prompt = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = Exception("LLM error")
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        with patch.object(rewrite, "_MULTI_QUERY_PROMPT", mock_prompt), \
             patch("app.rag.rewrite.get_llm"):
            result = rewrite.rewrite_query_multi("テストクエリ", n=3)

        assert result == ["テストクエリ"]


class TestRewriteQueryHyde:
    """rewrite_query_hyde 関数のテスト"""

    def test_returns_hypothetical_answer(self):
        """仮説的回答を返すことを確認"""
        from app.rag import rewrite

        mock_response = MagicMock()
        mock_response.content = "返品は、商品購入から30日以内であれば可能です。返品には、商品の状態が未使用であること、および元のパッケージが必要です。"

        mock_prompt = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = mock_response
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        with patch.object(rewrite, "_HYDE_PROMPT", mock_prompt), \
             patch("app.rag.rewrite.get_llm"):
            result = rewrite.rewrite_query_hyde("返品方法は？")

        assert "返品" in result
        assert len(result) > 10  # 単なるクエリではなく回答文書

    def test_hypothetical_answer_is_detailed(self):
        """仮説的回答が詳細であることを確認"""
        from app.rag import rewrite

        mock_response = MagicMock()
        mock_response.content = "当社の製品保証期間は、購入日から1年間です。この期間中に製品に欠陥が見つかった場合、無償で修理または交換いたします。保証を利用するには、購入証明書が必要です。"

        mock_prompt = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = mock_response
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        with patch.object(rewrite, "_HYDE_PROMPT", mock_prompt), \
             patch("app.rag.rewrite.get_llm"):
            result = rewrite.rewrite_query_hyde("保証期間について")

        assert len(result) > 50  # 詳細な回答

    def test_fallback_on_error(self):
        """エラー時は元のクエリを返すことを確認"""
        from app.rag import rewrite

        mock_prompt = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = Exception("LLM error")
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        with patch.object(rewrite, "_HYDE_PROMPT", mock_prompt), \
             patch("app.rag.rewrite.get_llm"):
            result = rewrite.rewrite_query_hyde("テストクエリ")

        assert result == "テストクエリ"

    def test_fallback_on_short_response(self):
        """短いレスポンス時は元のクエリを返すことを確認"""
        from app.rag import rewrite

        mock_response = MagicMock()
        mock_response.content = "短い"  # 10文字未満

        mock_prompt = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = mock_response
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        with patch.object(rewrite, "_HYDE_PROMPT", mock_prompt), \
             patch("app.rag.rewrite.get_llm"):
            result = rewrite.rewrite_query_hyde("テストクエリ")

        assert result == "テストクエリ"


class TestSettingsRetrievalStrategy:
    """設定の retrieval_strategy 関連テスト"""

    def test_default_retrieval_strategy(self):
        """デフォルトの検索戦略が standard であることを確認"""
        settings = Settings()
        assert settings.retrieval_strategy == "standard"

    def test_custom_retrieval_strategy(self):
        """カスタム検索戦略を設定できることを確認"""
        settings = Settings(retrieval_strategy="multi_query")
        assert settings.retrieval_strategy == "multi_query"

    def test_all_valid_strategies(self):
        """全ての有効な戦略値を設定できることを確認"""
        valid_strategies = ["standard", "multi_query", "hyde", "hybrid"]
        for strategy in valid_strategies:
            settings = Settings(retrieval_strategy=strategy)
            assert settings.retrieval_strategy == strategy

    def test_default_multi_query_count(self):
        """デフォルトの multi_query_count が 3 であることを確認"""
        settings = Settings()
        assert settings.multi_query_count == 3

    def test_custom_multi_query_count(self):
        """カスタム multi_query_count を設定できることを確認"""
        settings = Settings(multi_query_count=5)
        assert settings.multi_query_count == 5
