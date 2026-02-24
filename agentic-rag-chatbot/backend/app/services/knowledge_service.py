import logging
import uuid

from app.rag.bm25_store import BM25Store
from app.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class KnowledgeService:
    """ナレッジベースのドキュメント管理サービス"""

    _instance: "KnowledgeService | None" = None

    def __init__(self) -> None:
        self._vector_store = VectorStore.get_instance()
        self._bm25_store = BM25Store.get_instance()

    @classmethod
    def get_instance(cls) -> "KnowledgeService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    def list_documents(
        self,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """ドキュメント一覧を返す（total, items）"""
        try:
            all_docs = self._vector_store.get_all_documents()

            if category is not None:
                filtered = [
                    doc for doc in all_docs
                    if doc.get("metadata", {}).get("category") == category
                ]
            else:
                filtered = all_docs

            total = len(filtered)
            items = filtered[offset: offset + limit]

            return {"total": total, "items": items}
        except Exception as e:
            logger.error(f"KnowledgeService.list_documents failed: {e}")
            raise RuntimeError("ドキュメント一覧の取得に失敗しました") from e

    def get_document(self, doc_id: str) -> dict | None:
        """特定ドキュメントを返す"""
        try:
            result = self._vector_store._collection.get(
                ids=[doc_id],
                include=["documents", "metadatas"],
            )
            if not result or not result.get("ids") or len(result["ids"]) == 0:
                return None

            return {
                "id": result["ids"][0],
                "content": result["documents"][0] if result.get("documents") else "",
                "metadata": result["metadatas"][0] if result.get("metadatas") else {},
            }
        except Exception as e:
            logger.error(f"KnowledgeService.get_document failed for {doc_id}: {e}")
            raise RuntimeError(f"ドキュメント取得に失敗しました: {doc_id}") from e

    def add_document(self, content: str, metadata: dict) -> dict:
        """ドキュメントを追加しベクトルストア + BM25 に登録"""
        try:
            doc_id = str(uuid.uuid4())
            self._vector_store.add_documents(
                documents=[content],
                metadatas=[metadata],
                ids=[doc_id],
            )
            self._bm25_store.build_index_from_vector_store(self._vector_store)
            logger.info(f"KnowledgeService: added document {doc_id}")

            return {
                "id": doc_id,
                "content": content,
                "metadata": metadata,
            }
        except Exception as e:
            logger.error(f"KnowledgeService.add_document failed: {e}")
            raise RuntimeError("ドキュメントの追加に失敗しました") from e

    def delete_document(self, doc_id: str) -> bool:
        """ドキュメントを削除"""
        try:
            existing = self._vector_store._collection.get(
                ids=[doc_id],
                include=[],
            )
            if not existing or not existing.get("ids") or len(existing["ids"]) == 0:
                return False

            self._vector_store._collection.delete(ids=[doc_id])
            self._bm25_store.build_index_from_vector_store(self._vector_store)
            logger.info(f"KnowledgeService: deleted document {doc_id}")
            return True
        except Exception as e:
            logger.error(f"KnowledgeService.delete_document failed for {doc_id}: {e}")
            raise RuntimeError(f"ドキュメントの削除に失敗しました: {doc_id}") from e
