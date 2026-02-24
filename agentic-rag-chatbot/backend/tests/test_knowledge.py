"""ナレッジ管理サービス・APIのテスト"""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.jwt_handler import create_access_token
from app.main import app
from app.services.knowledge_service import KnowledgeService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_knowledge_service():
    """各テスト後にシングルトンをリセット"""
    KnowledgeService.reset_instance()
    yield
    KnowledgeService.reset_instance()


@pytest.fixture
def mock_vector_store():
    """VectorStore のモック"""
    store = MagicMock()
    store.get_all_documents.return_value = [
        {
            "id": "doc-001",
            "content": "サンプルドキュメント1",
            "metadata": {"title": "タイトル1", "category": "操作方法", "source": "manual"},
        },
        {
            "id": "doc-002",
            "content": "サンプルドキュメント2",
            "metadata": {"title": "タイトル2", "category": "FAQ", "source": "web"},
        },
    ]
    # collection の get/delete モック
    store._collection = MagicMock()
    store._collection.get.return_value = {
        "ids": ["doc-001"],
        "documents": ["サンプルドキュメント1"],
        "metadatas": [{"title": "タイトル1", "category": "操作方法", "source": "manual"}],
    }
    return store


@pytest.fixture
def mock_bm25_store():
    """BM25Store のモック"""
    return MagicMock()


@pytest.fixture
def knowledge_service(mock_vector_store, mock_bm25_store):
    """モックを注入した KnowledgeService インスタンス"""
    with (
        patch("app.services.knowledge_service.VectorStore.get_instance", return_value=mock_vector_store),
        patch("app.services.knowledge_service.BM25Store.get_instance", return_value=mock_bm25_store),
    ):
        service = KnowledgeService()
        KnowledgeService._instance = service
        yield service


@pytest.fixture
def auth_headers() -> dict:
    token = create_access_token({"sub": "admin-user"})
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# KnowledgeService Unit Tests
# ---------------------------------------------------------------------------

class TestKnowledgeServiceListDocuments:
    def test_list_all_documents(self, knowledge_service, mock_vector_store):
        """全ドキュメントが一覧取得できる"""
        result = knowledge_service.list_documents()
        assert result["total"] == 2
        assert len(result["items"]) == 2

    def test_list_documents_with_category_filter(self, knowledge_service):
        """カテゴリフィルタが機能する"""
        result = knowledge_service.list_documents(category="操作方法")
        assert result["total"] == 1
        assert result["items"][0]["id"] == "doc-001"

    def test_list_documents_with_unknown_category(self, knowledge_service):
        """存在しないカテゴリでは空リストが返る"""
        result = knowledge_service.list_documents(category="存在しないカテゴリ")
        assert result["total"] == 0
        assert result["items"] == []

    def test_list_documents_pagination(self, knowledge_service):
        """pagination が機能する"""
        result = knowledge_service.list_documents(limit=1, offset=0)
        assert len(result["items"]) == 1
        assert result["total"] == 2

        result2 = knowledge_service.list_documents(limit=1, offset=1)
        assert len(result2["items"]) == 1
        assert result2["items"][0]["id"] == "doc-002"

    def test_list_documents_offset_beyond_total(self, knowledge_service):
        """offset が総数を超える場合は空リストが返る"""
        result = knowledge_service.list_documents(offset=100)
        assert result["total"] == 2
        assert result["items"] == []


class TestKnowledgeServiceGetDocument:
    def test_get_existing_document(self, knowledge_service, mock_vector_store):
        """既存ドキュメントが取得できる"""
        doc = knowledge_service.get_document("doc-001")
        assert doc is not None
        assert doc["id"] == "doc-001"
        assert doc["content"] == "サンプルドキュメント1"
        assert doc["metadata"]["category"] == "操作方法"

    def test_get_nonexistent_document_returns_none(self, knowledge_service, mock_vector_store):
        """存在しないドキュメントで None が返る"""
        mock_vector_store._collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}
        doc = knowledge_service.get_document("nonexistent-id")
        assert doc is None


class TestKnowledgeServiceAddDocument:
    def test_add_document_returns_dict_with_id(self, knowledge_service):
        """追加したドキュメントがIDを持つ dict で返る"""
        content = "新しいドキュメントの本文"
        metadata = {"title": "新規", "category": "テスト", "source": "test"}

        result = knowledge_service.add_document(content=content, metadata=metadata)

        assert "id" in result
        assert len(result["id"]) > 0
        assert result["content"] == content
        assert result["metadata"] == metadata

    def test_add_document_calls_vector_store(self, knowledge_service, mock_vector_store):
        """ドキュメント追加時に vector_store.add_documents が呼ばれる"""
        knowledge_service.add_document(content="テスト", metadata={"title": "t"})
        mock_vector_store.add_documents.assert_called_once()

    def test_add_document_rebuilds_bm25_index(self, knowledge_service, mock_bm25_store):
        """ドキュメント追加後に BM25 インデックスがリビルドされる"""
        knowledge_service.add_document(content="テスト", metadata={"title": "t"})
        mock_bm25_store.build_index_from_vector_store.assert_called_once()

    def test_add_document_generates_unique_ids(self, knowledge_service):
        """複数追加時に異なる ID が生成される"""
        doc1 = knowledge_service.add_document(content="ドキュメント1", metadata={})
        doc2 = knowledge_service.add_document(content="ドキュメント2", metadata={})
        assert doc1["id"] != doc2["id"]

    def test_add_document_immutable_metadata(self, knowledge_service):
        """渡した metadata dict が変更されない（immutableパターン）"""
        metadata = {"title": "元のタイトル", "category": "テスト", "source": "manual"}
        original_metadata = {**metadata}
        knowledge_service.add_document(content="テスト", metadata=metadata)
        assert metadata == original_metadata


class TestKnowledgeServiceDeleteDocument:
    def test_delete_existing_document_returns_true(self, knowledge_service, mock_vector_store):
        """存在するドキュメントの削除が True を返す"""
        result = knowledge_service.delete_document("doc-001")
        assert result is True

    def test_delete_nonexistent_document_returns_false(self, knowledge_service, mock_vector_store):
        """存在しないドキュメントの削除が False を返す"""
        mock_vector_store._collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}
        result = knowledge_service.delete_document("nonexistent-id")
        assert result is False

    def test_delete_calls_collection_delete(self, knowledge_service, mock_vector_store):
        """削除時に collection.delete が呼ばれる"""
        knowledge_service.delete_document("doc-001")
        mock_vector_store._collection.delete.assert_called_once_with(ids=["doc-001"])

    def test_delete_rebuilds_bm25_index(self, knowledge_service, mock_bm25_store):
        """削除後に BM25 インデックスがリビルドされる"""
        knowledge_service.delete_document("doc-001")
        mock_bm25_store.build_index_from_vector_store.assert_called_once()

    def test_delete_nonexistent_does_not_call_collection_delete(self, knowledge_service, mock_vector_store):
        """存在しないドキュメントでは collection.delete が呼ばれない"""
        mock_vector_store._collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}
        knowledge_service.delete_document("nonexistent-id")
        mock_vector_store._collection.delete.assert_not_called()


# ---------------------------------------------------------------------------
# API Endpoint Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestKnowledgeApiListDocuments:
    async def test_list_documents_authenticated(self, auth_headers, mock_vector_store, mock_bm25_store):
        """認証付きで GET /api/admin/knowledge が正常に動作する"""
        with (
            patch("app.services.knowledge_service.VectorStore.get_instance", return_value=mock_vector_store),
            patch("app.services.knowledge_service.BM25Store.get_instance", return_value=mock_bm25_store),
        ):
            KnowledgeService._instance = KnowledgeService()
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/admin/knowledge", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "total" in data["data"]
        assert "items" in data["data"]

    async def test_list_documents_unauthenticated(self):
        """認証なしで 401 が返る"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/admin/knowledge")
        assert response.status_code == 401

    async def test_list_documents_invalid_token(self):
        """無効なトークンで 403 が返る"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/admin/knowledge",
                headers={"Authorization": "Bearer invalid.token.here"},
            )
        assert response.status_code == 403

    async def test_list_documents_category_filter(self, auth_headers, mock_vector_store, mock_bm25_store):
        """category クエリパラメータでフィルタリングできる"""
        with (
            patch("app.services.knowledge_service.VectorStore.get_instance", return_value=mock_vector_store),
            patch("app.services.knowledge_service.BM25Store.get_instance", return_value=mock_bm25_store),
        ):
            KnowledgeService._instance = KnowledgeService()
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get(
                    "/api/admin/knowledge?category=操作方法",
                    headers=auth_headers,
                )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 1


@pytest.mark.asyncio
class TestKnowledgeApiGetDocument:
    async def test_get_existing_document(self, auth_headers, mock_vector_store, mock_bm25_store):
        """存在するドキュメントが取得できる"""
        with (
            patch("app.services.knowledge_service.VectorStore.get_instance", return_value=mock_vector_store),
            patch("app.services.knowledge_service.BM25Store.get_instance", return_value=mock_bm25_store),
        ):
            KnowledgeService._instance = KnowledgeService()
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/admin/knowledge/doc-001", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "doc-001"

    async def test_get_nonexistent_document_returns_404(self, auth_headers, mock_vector_store, mock_bm25_store):
        """存在しないドキュメントで 404 が返る"""
        mock_vector_store._collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}
        with (
            patch("app.services.knowledge_service.VectorStore.get_instance", return_value=mock_vector_store),
            patch("app.services.knowledge_service.BM25Store.get_instance", return_value=mock_bm25_store),
        ):
            KnowledgeService._instance = KnowledgeService()
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/admin/knowledge/nonexistent", headers=auth_headers)

        assert response.status_code == 404

    async def test_get_document_unauthenticated(self):
        """認証なしで 401 が返る"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/admin/knowledge/doc-001")
        assert response.status_code == 401


@pytest.mark.asyncio
class TestKnowledgeApiAddDocument:
    async def test_add_document_success(self, auth_headers, mock_vector_store, mock_bm25_store):
        """ドキュメントが正常に追加できる"""
        payload = {
            "content": "新しいドキュメントの内容",
            "metadata": {
                "title": "初期設定ガイド",
                "category": "操作方法",
                "source": "manual",
            },
        }
        with (
            patch("app.services.knowledge_service.VectorStore.get_instance", return_value=mock_vector_store),
            patch("app.services.knowledge_service.BM25Store.get_instance", return_value=mock_bm25_store),
        ):
            KnowledgeService._instance = KnowledgeService()
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/admin/knowledge", json=payload, headers=auth_headers)

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "id" in data["data"]
        assert data["data"]["content"] == "新しいドキュメントの内容"

    async def test_add_document_empty_content_fails(self, auth_headers):
        """空のコンテンツで 422 が返る"""
        payload = {"content": "", "metadata": {}}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/admin/knowledge", json=payload, headers=auth_headers)
        assert response.status_code == 422

    async def test_add_document_unauthenticated(self):
        """認証なしで 401 が返る"""
        payload = {"content": "テスト", "metadata": {"title": "t", "category": "c", "source": "s"}}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/admin/knowledge", json=payload)
        assert response.status_code == 401

    async def test_add_document_with_default_metadata(self, auth_headers, mock_vector_store, mock_bm25_store):
        """metadata を省略してもデフォルト値でドキュメントが追加できる"""
        payload = {"content": "本文のみのドキュメント"}
        with (
            patch("app.services.knowledge_service.VectorStore.get_instance", return_value=mock_vector_store),
            patch("app.services.knowledge_service.BM25Store.get_instance", return_value=mock_bm25_store),
        ):
            KnowledgeService._instance = KnowledgeService()
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/admin/knowledge", json=payload, headers=auth_headers)

        assert response.status_code == 201


@pytest.mark.asyncio
class TestKnowledgeApiDeleteDocument:
    async def test_delete_existing_document(self, auth_headers, mock_vector_store, mock_bm25_store):
        """存在するドキュメントが削除できる"""
        with (
            patch("app.services.knowledge_service.VectorStore.get_instance", return_value=mock_vector_store),
            patch("app.services.knowledge_service.BM25Store.get_instance", return_value=mock_bm25_store),
        ):
            KnowledgeService._instance = KnowledgeService()
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.delete("/api/admin/knowledge/doc-001", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["deleted"] == "doc-001"

    async def test_delete_nonexistent_document_returns_404(self, auth_headers, mock_vector_store, mock_bm25_store):
        """存在しないドキュメントの削除で 404 が返る"""
        mock_vector_store._collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}
        with (
            patch("app.services.knowledge_service.VectorStore.get_instance", return_value=mock_vector_store),
            patch("app.services.knowledge_service.BM25Store.get_instance", return_value=mock_bm25_store),
        ):
            KnowledgeService._instance = KnowledgeService()
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.delete("/api/admin/knowledge/nonexistent", headers=auth_headers)

        assert response.status_code == 404

    async def test_delete_document_unauthenticated(self):
        """認証なしで 401 が返る"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete("/api/admin/knowledge/doc-001")
        assert response.status_code == 401

    async def test_delete_document_invalid_token(self):
        """無効なトークンで 403 が返る"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete(
                "/api/admin/knowledge/doc-001",
                headers={"Authorization": "Bearer invalid.token.here"},
            )
        assert response.status_code == 403
