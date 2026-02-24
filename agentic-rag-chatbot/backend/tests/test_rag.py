import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import chromadb
import pytest

from app.config.settings import Settings
from app.rag.document_loader import _build_header_prefix, _generate_doc_id, _infer_category, load_markdown_file
from app.rag.retriever import retrieve_documents
from app.rag.vector_store import VectorStore


# ---------------------------------------------------------------------------
# ヘルパー: テスト専用の VectorStore を作成する
# ---------------------------------------------------------------------------


def _make_ephemeral_store() -> VectorStore:
    """EphemeralClient とユニークなコレクション名を使って孤立したストアを作成する"""
    client = chromadb.EphemeralClient()
    collection_name = f"test_{uuid.uuid4().hex}"
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    store = VectorStore.__new__(VectorStore)
    store._client = client
    store._collection = collection
    return store


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_vector_store_singleton():
    """各テスト前後にシングルトンをリセットして汚染を防ぐ"""
    VectorStore.reset_instance()
    yield
    VectorStore.reset_instance()


@pytest.fixture
def ephemeral_vector_store():
    """EphemeralClient を使った一時的な VectorStore を返し、シングルトンに登録するフィクスチャ"""
    store = _make_ephemeral_store()
    VectorStore._instance = store
    return store


@pytest.fixture
def sample_markdown_file(tmp_path: Path) -> Path:
    """テスト用 Markdown ファイルを tmp_path に作成して返す"""
    content = """# テスト製品ガイド

## 初期設定

初期設定の手順を説明します。

### ログイン方法

1. URLにアクセスします。
2. メールアドレスとパスワードを入力します。
3. ログインボタンをクリックします。

## ダッシュボード

ダッシュボードには各種情報が表示されます。
"""
    md_file = tmp_path / "product_guide.md"
    md_file.write_text(content, encoding="utf-8")
    return md_file


# ---------------------------------------------------------------------------
# VectorStore のシングルトンパターンテスト
# ---------------------------------------------------------------------------


class TestVectorStoreSingleton:
    def test_get_instance_returns_same_instance(self, ephemeral_vector_store):
        """get_instance() が同一インスタンスを返すことを確認"""
        instance1 = VectorStore.get_instance()
        instance2 = VectorStore.get_instance()
        assert instance1 is instance2

    def test_reset_instance_clears_singleton(self):
        """reset_instance() 後に get_instance() が新しいインスタンスを返すことを確認"""
        store1 = _make_ephemeral_store()
        VectorStore._instance = store1
        instance1 = VectorStore.get_instance()
        assert instance1 is store1

        VectorStore.reset_instance()
        assert VectorStore._instance is None

        # 新しいストアを注入
        store2 = _make_ephemeral_store()
        VectorStore._instance = store2
        instance2 = VectorStore.get_instance()
        assert instance2 is store2
        assert instance1 is not instance2

    def test_reset_instance_sets_none(self):
        """reset_instance() が _instance を None にすることを確認"""
        VectorStore._instance = MagicMock()
        VectorStore.reset_instance()
        assert VectorStore._instance is None


# ---------------------------------------------------------------------------
# VectorStore の add_documents / query / count テスト
# ---------------------------------------------------------------------------


class TestVectorStoreOperations:
    def test_add_documents_increases_count(self, ephemeral_vector_store):
        """add_documents でドキュメント数が増えることを確認"""
        assert ephemeral_vector_store.count == 0
        ephemeral_vector_store.add_documents(
            documents=["テストドキュメント1", "テストドキュメント2"],
            metadatas=[{"category": "操作方法"}, {"category": "操作方法"}],
            ids=["id1", "id2"],
        )
        assert ephemeral_vector_store.count == 2

    def test_add_documents_auto_generates_ids(self, ephemeral_vector_store):
        """ids を省略した場合に自動生成されることを確認"""
        assert ephemeral_vector_store.count == 0
        ephemeral_vector_store.add_documents(
            documents=["ドキュメントA", "ドキュメントB"],
        )
        assert ephemeral_vector_store.count == 2

    def test_query_returns_results(self, ephemeral_vector_store):
        """query が類似ドキュメントを返すことを確認"""
        ephemeral_vector_store.add_documents(
            documents=["ログイン方法について説明します", "料金プランの詳細"],
            metadatas=[{"category": "操作方法"}, {"category": "契約・料金"}],
            ids=["doc1", "doc2"],
        )
        results = ephemeral_vector_store.query(query_text="ログイン", n_results=1)
        assert results is not None
        assert "documents" in results
        assert len(results["documents"][0]) == 1

    def test_query_returns_multiple_results(self, ephemeral_vector_store):
        """n_results に応じた件数が返ることを確認"""
        docs = [f"ドキュメント {i}" for i in range(5)]
        ephemeral_vector_store.add_documents(
            documents=docs,
            ids=[f"id{i}" for i in range(5)],
        )
        results = ephemeral_vector_store.query(query_text="ドキュメント", n_results=3)
        assert len(results["documents"][0]) == 3

    def test_query_with_where_filter(self, ephemeral_vector_store):
        """where フィルターが機能することを確認"""
        ephemeral_vector_store.add_documents(
            documents=["操作方法のドキュメント", "料金に関するドキュメント"],
            metadatas=[{"category": "操作方法"}, {"category": "契約・料金"}],
            ids=["op_doc", "contract_doc"],
        )
        results = ephemeral_vector_store.query(
            query_text="ドキュメント",
            n_results=5,
            where={"category": "操作方法"},
        )
        assert len(results["documents"][0]) == 1

    def test_count_property(self, ephemeral_vector_store):
        """count プロパティがドキュメント数を正しく返すことを確認"""
        assert ephemeral_vector_store.count == 0
        ephemeral_vector_store.add_documents(
            documents=["doc1", "doc2", "doc3"],
            ids=["a", "b", "c"],
        )
        assert ephemeral_vector_store.count == 3


# ---------------------------------------------------------------------------
# document_loader のテスト
# ---------------------------------------------------------------------------


class TestDocumentLoader:
    def test_load_markdown_file_returns_chunks(self, sample_markdown_file: Path):
        """Markdown ファイルがチャンクに分割されることを確認"""
        chunks = load_markdown_file(sample_markdown_file)
        assert len(chunks) > 0

    def test_load_markdown_file_chunk_structure(self, sample_markdown_file: Path):
        """各チャンクが必要なキーを持つことを確認"""
        chunks = load_markdown_file(sample_markdown_file)
        for chunk in chunks:
            assert "content" in chunk
            assert "metadata" in chunk
            assert "id" in chunk

    def test_load_markdown_file_metadata_has_source(self, sample_markdown_file: Path):
        """メタデータに source フィールドが含まれることを確認"""
        chunks = load_markdown_file(sample_markdown_file)
        for chunk in chunks:
            assert "source" in chunk["metadata"]
            assert chunk["metadata"]["source"] == sample_markdown_file.name

    def test_load_markdown_file_metadata_has_category(self, sample_markdown_file: Path):
        """メタデータに category フィールドが含まれることを確認"""
        chunks = load_markdown_file(sample_markdown_file)
        for chunk in chunks:
            assert "category" in chunk["metadata"]
            assert chunk["metadata"]["category"] == "操作方法"

    def test_load_markdown_file_ids_are_unique(self, sample_markdown_file: Path):
        """チャンクのIDが一意であることを確認"""
        chunks = load_markdown_file(sample_markdown_file)
        ids = [c["id"] for c in chunks]
        assert len(ids) == len(set(ids))

    def test_load_markdown_file_content_not_empty(self, sample_markdown_file: Path):
        """チャンクのコンテンツが空でないことを確認"""
        chunks = load_markdown_file(sample_markdown_file)
        for chunk in chunks:
            assert chunk["content"].strip() != ""


# ---------------------------------------------------------------------------
# チャンキング最適化のテスト
# ---------------------------------------------------------------------------


class TestChunkingOptimization:
    def test_chunk_size_uses_settings(self, tmp_path: Path):
        """chunk_size が settings の値に基づくことを確認"""
        # セパレーター（句点）を含む長い日本語テキストを使用
        sentences = ["あ" * 60 + "。"] * 20
        content = "# タイトル\n\n" + "".join(sentences)
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        custom_settings = Settings(chunk_size=100, chunk_overlap=10)
        with patch("app.rag.document_loader.get_settings", return_value=custom_settings):
            chunks = load_markdown_file(md_file)

        # chunk_size=100 の場合、長いコンテンツは複数チャンクに分割される
        assert len(chunks) > 1

    def test_chunk_size_large_produces_fewer_chunks(self, tmp_path: Path):
        """chunk_size が大きい場合は chunk_size が小さい場合より少ないチャンクになることを確認"""
        # セパレーター（句点）を含む長いテキスト
        sentences = ["あいうえお" * 10 + "。"] * 30
        content = "# タイトル\n\n" + "".join(sentences)
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        small_settings = Settings(chunk_size=100, chunk_overlap=10)
        large_settings = Settings(chunk_size=5000, chunk_overlap=500)

        with patch("app.rag.document_loader.get_settings", return_value=small_settings):
            small_chunks = load_markdown_file(md_file)

        with patch("app.rag.document_loader.get_settings", return_value=large_settings):
            large_chunks = load_markdown_file(md_file)

        assert len(small_chunks) > len(large_chunks)

    def test_header_prefix_added_to_content(self, sample_markdown_file: Path):
        """ヘッダー階層プレフィックスがコンテンツの先頭に付与されることを確認"""
        chunks = load_markdown_file(sample_markdown_file)
        # ヘッダーを持つチャンクはプレフィックスを持つ
        prefixed = [c for c in chunks if c["content"].startswith("「")]
        assert len(prefixed) > 0

    def test_header_prefix_format(self, sample_markdown_file: Path):
        """プレフィックスが「タイトル > セクション」形式であることを確認"""
        chunks = load_markdown_file(sample_markdown_file)
        for chunk in chunks:
            content = chunk["content"]
            if content.startswith("「"):
                # 「...」\n の形式を確認
                assert "」\n" in content

    def test_missing_headers_no_error(self, tmp_path: Path):
        """ヘッダーが欠損していてもエラーにならないことを確認"""
        content = "ヘッダーなしのコンテンツです。"
        md_file = tmp_path / "noheader.md"
        md_file.write_text(content, encoding="utf-8")

        chunks = load_markdown_file(md_file)
        assert len(chunks) > 0
        # ヘッダーなしのチャンクはプレフィックスなし
        for chunk in chunks:
            assert chunk["content"].strip() != ""


class TestBuildHeaderPrefix:
    def test_all_headers_present(self):
        """title, section, subsection がすべてある場合"""
        metadata = {"title": "製品ガイド", "section": "基本操作", "subsection": "ログイン方法"}
        prefix = _build_header_prefix(metadata)
        assert prefix == "「製品ガイド > 基本操作 > ログイン方法」\n"

    def test_only_title(self):
        """title のみある場合"""
        metadata = {"title": "製品ガイド"}
        prefix = _build_header_prefix(metadata)
        assert prefix == "「製品ガイド」\n"

    def test_title_and_section(self):
        """title と section がある場合"""
        metadata = {"title": "製品ガイド", "section": "基本操作"}
        prefix = _build_header_prefix(metadata)
        assert prefix == "「製品ガイド > 基本操作」\n"

    def test_empty_metadata_returns_empty_string(self):
        """ヘッダーが一切ない場合は空文字列を返す"""
        metadata = {}
        prefix = _build_header_prefix(metadata)
        assert prefix == ""

    def test_none_values_ignored(self):
        """None値のヘッダーは無視される"""
        metadata = {"title": "製品ガイド", "section": None, "subsection": None}
        prefix = _build_header_prefix(metadata)
        assert prefix == "「製品ガイド」\n"


# ---------------------------------------------------------------------------
# _infer_category のテスト
# ---------------------------------------------------------------------------


class TestInferCategory:
    def test_product_guide_returns_operation(self):
        """product_guide ファイルが「操作方法」カテゴリになることを確認"""
        assert _infer_category("product_guide") == "操作方法"

    def test_troubleshooting_returns_trouble(self):
        """troubleshooting ファイルが「障害・トラブル」カテゴリになることを確認"""
        assert _infer_category("troubleshooting") == "障害・トラブル"

    def test_contracts_returns_contract(self):
        """contracts ファイルが「契約・料金」カテゴリになることを確認"""
        assert _infer_category("contracts") == "契約・料金"

    def test_unknown_stem_returns_other(self):
        """不明なファイル名が「その他」カテゴリになることを確認"""
        assert _infer_category("unknown_file") == "その他"
        assert _infer_category("readme") == "その他"
        assert _infer_category("") == "その他"


# ---------------------------------------------------------------------------
# _generate_doc_id のテスト
# ---------------------------------------------------------------------------


class TestGenerateDocId:
    def test_generates_string(self):
        """ドキュメントIDが文字列として生成されることを確認"""
        doc_id = _generate_doc_id("テストコンテンツ", "test.md")
        assert isinstance(doc_id, str)

    def test_same_inputs_same_id(self):
        """同じ入力からは同じIDが生成されることを確認"""
        id1 = _generate_doc_id("コンテンツ", "source.md")
        id2 = _generate_doc_id("コンテンツ", "source.md")
        assert id1 == id2

    def test_different_content_different_id(self):
        """異なるコンテンツからは異なるIDが生成されることを確認"""
        id1 = _generate_doc_id("コンテンツA", "source.md")
        id2 = _generate_doc_id("コンテンツB", "source.md")
        assert id1 != id2

    def test_different_source_different_id(self):
        """同じコンテンツでも異なるソースからは異なるIDが生成されることを確認"""
        id1 = _generate_doc_id("同じコンテンツ", "source_a.md")
        id2 = _generate_doc_id("同じコンテンツ", "source_b.md")
        assert id1 != id2


# ---------------------------------------------------------------------------
# retrieve_documents のテスト
# ---------------------------------------------------------------------------


class TestRetrieveDocuments:
    def test_retrieve_returns_list(self, ephemeral_vector_store):
        """retrieve_documents がリストを返すことを確認"""
        ephemeral_vector_store.add_documents(
            documents=["ログイン方法の説明"],
            metadatas=[{"category": "操作方法"}],
            ids=["test_doc"],
        )
        results = retrieve_documents("ログイン", n_results=1)
        assert isinstance(results, list)

    def test_retrieve_returns_formatted_documents(self, ephemeral_vector_store):
        """検索結果が正しい形式で返ることを確認"""
        ephemeral_vector_store.add_documents(
            documents=["パスワードのリセット方法"],
            metadatas=[{"category": "操作方法"}],
            ids=["reset_doc"],
        )
        results = retrieve_documents("パスワード", n_results=1)
        assert len(results) > 0
        doc = results[0]
        assert "content" in doc
        assert "metadata" in doc
        assert "relevance_score" in doc
        assert "id" in doc

    def test_retrieve_relevance_score_in_range(self, ephemeral_vector_store):
        """relevance_score が 0〜1 の範囲内であることを確認"""
        ephemeral_vector_store.add_documents(
            documents=["エラーが発生した場合の対処法"],
            metadatas=[{"category": "障害・トラブル"}],
            ids=["error_doc"],
        )
        results = retrieve_documents("エラー対処", n_results=1)
        for doc in results:
            assert 0.0 <= doc["relevance_score"] <= 1.0

    def test_retrieve_with_category_filter(self, ephemeral_vector_store):
        """カテゴリフィルターが機能することを確認"""
        ephemeral_vector_store.add_documents(
            documents=["料金プランの説明", "ログインに関する説明"],
            metadatas=[
                {"category": "契約・料金"},
                {"category": "操作方法"},
            ],
            ids=["contract_doc", "operation_doc"],
        )
        results = retrieve_documents("説明", n_results=5, category="契約・料金")
        assert len(results) == 1
        assert results[0]["metadata"]["category"] == "契約・料金"

    def test_retrieve_empty_store_returns_empty_list(self, ephemeral_vector_store):
        """ドキュメントが0件の場合は空リストが返ることを確認"""
        results = retrieve_documents("何か検索", n_results=5)
        assert results == []
