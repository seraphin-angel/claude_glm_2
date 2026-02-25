"""BM25Store と hybrid_retrieve のテスト"""
import pytest


# --- フィクスチャ ---

@pytest.fixture(autouse=True)
def reset_bm25():
    """各テスト前後に BM25Store シングルトンをリセットする"""
    from app.rag.bm25_store import BM25Store
    BM25Store.reset_instance()
    yield
    BM25Store.reset_instance()


SAMPLE_DOCS = [
    {"content": "製品の設定方法について説明します。初期設定は簡単です。", "metadata": {"category": "操作方法"}, "id": "doc_1"},
    {"content": "エラーが発生した場合のトラブルシューティングガイドです。", "metadata": {"category": "障害・トラブル"}, "id": "doc_2"},
    {"content": "料金プランと契約条件についての詳細情報です。", "metadata": {"category": "契約・料金"}, "id": "doc_3"},
    {"content": "ネットワーク接続の問題を解決する方法を解説します。", "metadata": {"category": "障害・トラブル"}, "id": "doc_4"},
    {"content": "アカウント管理と設定変更の手順を紹介します。", "metadata": {"category": "操作方法"}, "id": "doc_5"},
]


# --- BM25Store シングルトンテスト ---

class TestBM25StoreSingleton:
    def test_get_instance_returns_same_instance(self):
        from app.rag.bm25_store import BM25Store

        instance1 = BM25Store.get_instance()
        instance2 = BM25Store.get_instance()
        assert instance1 is instance2

    def test_reset_instance_creates_new_instance(self):
        from app.rag.bm25_store import BM25Store

        instance1 = BM25Store.get_instance()
        BM25Store.reset_instance()
        instance2 = BM25Store.get_instance()
        assert instance1 is not instance2


# --- build_index + search テスト ---

class TestBM25StoreSearch:
    def test_build_index_and_search(self):
        from app.rag.bm25_store import BM25Store

        store = BM25Store.get_instance()
        store.build_index(SAMPLE_DOCS)

        results = store.search("エラー トラブル", top_k=3)
        assert len(results) > 0
        assert all("content" in r for r in results)
        assert all("metadata" in r for r in results)
        assert all("id" in r for r in results)
        assert all("bm25_score" in r for r in results)

    def test_search_returns_relevant_result(self):
        from app.rag.bm25_store import BM25Store

        store = BM25Store.get_instance()
        store.build_index(SAMPLE_DOCS)

        results = store.search("料金 契約", top_k=5)
        ids = [r["id"] for r in results]
        assert "doc_3" in ids

    def test_search_without_index_returns_empty(self):
        from app.rag.bm25_store import BM25Store

        store = BM25Store.get_instance()
        results = store.search("テスト", top_k=5)
        assert results == []

    def test_search_with_empty_documents_returns_empty(self):
        from app.rag.bm25_store import BM25Store

        store = BM25Store.get_instance()
        store.build_index([])
        results = store.search("テスト", top_k=5)
        assert results == []

    def test_search_respects_top_k(self):
        from app.rag.bm25_store import BM25Store

        store = BM25Store.get_instance()
        store.build_index(SAMPLE_DOCS)

        results = store.search("設定", top_k=2)
        assert len(results) <= 2

    def test_search_scores_are_float(self):
        from app.rag.bm25_store import BM25Store

        store = BM25Store.get_instance()
        store.build_index(SAMPLE_DOCS)

        results = store.search("接続 ネットワーク", top_k=3)
        for r in results:
            assert isinstance(r["bm25_score"], float)


# --- fugashi 分かち書きテスト ---

class TestTokenization:
    def test_tokenize_japanese(self):
        import fugashi

        tagger = fugashi.Tagger()
        text = "製品の設定方法"
        tokens = [word.surface for word in tagger(text) if word.surface.strip()]
        assert len(tokens) > 0
        assert all(isinstance(t, str) for t in tokens)

    def test_tokenize_produces_meaningful_tokens(self):
        import fugashi

        tagger = fugashi.Tagger()
        text = "エラーが発生した場合"
        tokens = [word.surface for word in tagger(text) if word.surface.strip()]
        assert "エラー" in tokens

    def test_tokenize_empty_string(self):
        import fugashi

        tagger = fugashi.Tagger()
        tokens = [word.surface for word in tagger("") if word.surface.strip()]
        assert tokens == []


# --- hybrid_retrieve RRF テスト ---

class TestHybridRetrieve:
    def _make_mock_vector_results(self):
        return [
            {"content": "製品の設定方法について説明します。", "metadata": {"category": "操作方法"}, "relevance_score": 0.9, "id": "doc_1"},
            {"content": "エラーが発生した場合のトラブルシューティング。", "metadata": {"category": "障害・トラブル"}, "relevance_score": 0.7, "id": "doc_2"},
        ]

    def test_hybrid_retrieve_returns_list(self, monkeypatch):
        from app.rag import retriever
        from app.rag.bm25_store import BM25Store

        store = BM25Store.get_instance()
        store.build_index(SAMPLE_DOCS)

        monkeypatch.setattr(retriever, "retrieve_documents", lambda **_: self._make_mock_vector_results())

        results = retriever.hybrid_retrieve(query="設定 エラー", n_results=3)
        assert isinstance(results, list)
        assert len(results) <= 3

    def test_hybrid_retrieve_contains_required_fields(self, monkeypatch):
        from app.rag import retriever
        from app.rag.bm25_store import BM25Store

        store = BM25Store.get_instance()
        store.build_index(SAMPLE_DOCS)

        monkeypatch.setattr(retriever, "retrieve_documents", lambda **_: self._make_mock_vector_results())

        results = retriever.hybrid_retrieve(query="設定", n_results=5)
        for r in results:
            assert "content" in r
            assert "metadata" in r
            assert "relevance_score" in r
            assert "id" in r

    def test_hybrid_retrieve_rrf_merges_results(self, monkeypatch):
        """RRF によって BM25 のみにヒットする doc_3 がマージされることを確認"""
        from app.rag import retriever
        from app.rag.bm25_store import BM25Store

        store = BM25Store.get_instance()
        store.build_index(SAMPLE_DOCS)

        monkeypatch.setattr(
            retriever,
            "retrieve_documents",
            lambda **_: [
                {"content": "製品の設定方法", "metadata": {}, "relevance_score": 0.9, "id": "doc_1"},
            ],
        )

        results = retriever.hybrid_retrieve(query="料金 契約", n_results=5)
        ids = [r["id"] for r in results]
        assert "doc_3" in ids


# --- alpha=1.0 でベクトルのみになるテスト ---

class TestAlphaFallback:
    def test_alpha_1_skips_bm25(self, monkeypatch):
        from app.config.settings import Settings, get_settings
        from app.rag import retriever
        from app.rag.bm25_store import BM25Store

        vector_results = [
            {"content": "ベクトル検索結果", "metadata": {}, "relevance_score": 0.9, "id": "vec_1"},
        ]

        monkeypatch.setattr(retriever, "retrieve_documents", lambda **_: vector_results)

        bm25_call_count = {"count": 0}
        original_search = BM25Store.search

        def mock_search(self, query, top_k=10):
            bm25_call_count["count"] += 1
            return []

        monkeypatch.setattr(BM25Store, "search", mock_search)
        monkeypatch.setattr(
            retriever,
            "get_settings",
            lambda: Settings(hybrid_search_alpha=1.0, bm25_top_k=10, reranker_enabled=False),
        )

        results = retriever.hybrid_retrieve(query="テスト", n_results=5)
        assert bm25_call_count["count"] == 0
        assert results == vector_results

    def test_alpha_less_than_1_uses_bm25(self, monkeypatch):
        from app.config.settings import Settings
        from app.rag import retriever
        from app.rag.bm25_store import BM25Store

        store = BM25Store.get_instance()
        store.build_index(SAMPLE_DOCS)

        monkeypatch.setattr(
            retriever,
            "retrieve_documents",
            lambda **_: [{"content": "テスト", "metadata": {}, "relevance_score": 0.8, "id": "doc_1"}],
        )
        monkeypatch.setattr(
            retriever,
            "get_settings",
            lambda: Settings(hybrid_search_alpha=0.5, bm25_top_k=10, reranker_enabled=False),
        )

        results = retriever.hybrid_retrieve(query="エラー", n_results=5)
        assert isinstance(results, list)
