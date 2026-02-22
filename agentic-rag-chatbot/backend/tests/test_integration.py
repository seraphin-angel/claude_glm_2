"""
結合テスト:
1. FastAPI アプリ全体のルーティングテスト
   - GET /api/health が正しくレスポンスを返す
   - POST /api/chat のバリデーション（正常系・異常系）
   - POST /api/chat/resume/{thread_id} のバリデーション

2. RAG ドキュメントロードの結合テスト
   - load_all_documents がサンプルドキュメントを正しくロードする
   - retrieve_documents が検索結果を返す

3. ChatService の結合テスト（エージェントはモック）
   - start_chat がスレッドIDを返す
   - キューにイベントが送出される
   - resume_chat がキューを再作成する
   - cleanup がリソースを解放する

4. ストリームイベントのシリアライズテスト
   - StreamEvent が正しく JSON シリアライズされる
   - 各イベントタイプのシリアライズ

注意:
- LLM呼び出し（ChatOpenAI）は全てモック
- ChromaDB はテンポラリディレクトリを使用
- エージェント（get_agent）はモックを使用
"""

import asyncio
import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import chromadb
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.messages import StreamEvent, StreamEventType
from app.rag.vector_store import VectorStore


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_vector_store():
    """テスト間でVectorStoreシングルトンをリセット"""
    VectorStore.reset_instance()
    yield
    VectorStore.reset_instance()


def _make_ephemeral_store() -> VectorStore:
    """インメモリChromaDBを使った孤立したVectorStoreを作成"""
    client = chromadb.EphemeralClient()
    collection_name = f"test_integ_{uuid.uuid4().hex}"
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    store = VectorStore.__new__(VectorStore)
    store._client = client
    store._collection = collection
    return store


# ---------------------------------------------------------------------------
# 1. FastAPI アプリ全体のルーティングテスト
# ---------------------------------------------------------------------------


class TestAppRouting:
    """FastAPIアプリのルーティング結合テスト"""

    async def test_health_endpoint_returns_200(self, client: AsyncClient):
        """GET /api/health が 200 OK を返すこと"""
        response = await client.get("/api/health")
        assert response.status_code == 200

    async def test_health_endpoint_returns_ok_status(self, client: AsyncClient):
        """GET /api/health が status=ok を含むこと"""
        response = await client.get("/api/health")
        data = response.json()
        assert data["status"] == "ok"

    async def test_health_endpoint_returns_version(self, client: AsyncClient):
        """GET /api/health が version フィールドを含むこと"""
        response = await client.get("/api/health")
        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0

    async def test_chat_endpoint_validates_empty_message(self, client: AsyncClient, auth_headers: dict):
        """POST /api/chat: 空メッセージで 422 バリデーションエラーを返すこと"""
        response = await client.post("/api/chat", json={"message": ""}, headers=auth_headers)
        assert response.status_code == 422

    async def test_chat_endpoint_validates_missing_message(self, client: AsyncClient, auth_headers: dict):
        """POST /api/chat: message フィールドなしで 422 を返すこと"""
        response = await client.post("/api/chat", json={}, headers=auth_headers)
        assert response.status_code == 422

    async def test_chat_endpoint_validates_long_message(self, client: AsyncClient, auth_headers: dict):
        """POST /api/chat: 2001文字超で 422 を返すこと"""
        response = await client.post(
            "/api/chat",
            json={"message": "あ" * 2001},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_chat_endpoint_accepts_valid_message(self, client: AsyncClient, auth_headers: dict):
        """POST /api/chat: 正常なメッセージで 200 を返すこと"""
        mock_service = MagicMock()
        mock_service.start_chat = AsyncMock(return_value="integration-thread-id")

        with patch("app.api.chat.get_chat_service", return_value=mock_service):
            response = await client.post(
                "/api/chat",
                json={"message": "製品の使い方を教えてください"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "thread_id" in data["data"]
        assert data["data"]["status"] == "streaming"

    async def test_chat_endpoint_accepts_max_length_message(self, client: AsyncClient, auth_headers: dict):
        """POST /api/chat: 2000文字のメッセージ（上限）で 200 を返すこと"""
        mock_service = MagicMock()
        mock_service.start_chat = AsyncMock(return_value="thread-max-len")

        with patch("app.api.chat.get_chat_service", return_value=mock_service):
            response = await client.post(
                "/api/chat",
                json={"message": "あ" * 2000},
                headers=auth_headers,
            )

        assert response.status_code == 200

    async def test_resume_endpoint_validates_empty_response(self, client: AsyncClient, auth_headers: dict):
        """POST /api/chat/resume: 空の response で 422 を返すこと"""
        response = await client.post(
            "/api/chat/resume/some-thread",
            json={"request_id": "req-001", "response": ""},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_resume_endpoint_validates_missing_fields(self, client: AsyncClient, auth_headers: dict):
        """POST /api/chat/resume: 必須フィールドなしで 422 を返すこと"""
        response = await client.post(
            "/api/chat/resume/some-thread",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_resume_endpoint_accepts_valid_request(self, client: AsyncClient, auth_headers: dict):
        """POST /api/chat/resume: 正常なリクエストで 200 を返すこと"""
        test_thread_uuid = "550e8400-e29b-41d4-a716-446655440000"
        mock_service = MagicMock()
        mock_service.resume_chat = AsyncMock()
        mock_service._queues = {test_thread_uuid: MagicMock()}

        with patch("app.api.chat.get_chat_service", return_value=mock_service):
            response = await client.post(
                f"/api/chat/resume/{test_thread_uuid}",
                json={"request_id": "req-001", "response": "技術サポート"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_nonexistent_endpoint_returns_404(self, client: AsyncClient):
        """存在しないエンドポイントに 404 が返ること"""
        response = await client.get("/api/nonexistent")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# 2. RAG ドキュメントロードの結合テスト
# ---------------------------------------------------------------------------


class TestRagDocumentLoadIntegration:
    """RAG ドキュメントロードの結合テスト"""

    def test_load_all_documents_from_sample_docs(self, tmp_path: Path):
        """サンプルドキュメントディレクトリからドキュメントをロードできること"""
        from app.rag.document_loader import load_all_documents

        # テスト用ドキュメントを作成
        docs_dir = tmp_path / "sample_docs"
        docs_dir.mkdir()
        (docs_dir / "product_guide.md").write_text(
            "# 製品ガイド\n\n## 初期設定\n\n初期設定の手順を説明します。\n\n### ログイン\nURLにアクセスしてください。",
            encoding="utf-8",
        )
        (docs_dir / "troubleshooting.md").write_text(
            "# トラブルシューティング\n\n## エラー対処\n\nエラーが発生した場合の対処法。",
            encoding="utf-8",
        )

        # インメモリVectorStoreを注入
        store = _make_ephemeral_store()
        VectorStore._instance = store

        count = load_all_documents(str(docs_dir))
        assert count > 0

    def test_load_all_documents_returns_positive_count(self, tmp_path: Path):
        """load_all_documents が正のチャンク数を返すこと"""
        from app.rag.document_loader import load_all_documents

        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "test.md").write_text(
            "# テスト\n\n## セクション1\n\nコンテンツがここにあります。\n\n### サブセクション\n詳細説明テキスト。",
            encoding="utf-8",
        )

        store = _make_ephemeral_store()
        VectorStore._instance = store

        count = load_all_documents(str(docs_dir))
        assert count > 0
        assert store.count > 0

    def test_load_all_documents_raises_for_missing_dir(self):
        """存在しないディレクトリで FileNotFoundError が発生すること"""
        from app.rag.document_loader import load_all_documents

        with pytest.raises(FileNotFoundError):
            load_all_documents("/nonexistent/path/docs")

    def test_load_all_documents_empty_dir_returns_zero(self, tmp_path: Path):
        """空ディレクトリで 0 が返ること"""
        from app.rag.document_loader import load_all_documents

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        store = _make_ephemeral_store()
        VectorStore._instance = store

        count = load_all_documents(str(empty_dir))
        assert count == 0

    def test_retrieve_documents_after_load(self, tmp_path: Path):
        """ドキュメントロード後に検索結果が返ること"""
        from app.rag.document_loader import load_all_documents
        from app.rag.retriever import retrieve_documents

        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "product_guide.md").write_text(
            "# 製品ガイド\n\n## ログイン方法\n\nURLにアクセスしてメールアドレスとパスワードを入力してください。",
            encoding="utf-8",
        )

        store = _make_ephemeral_store()
        VectorStore._instance = store

        load_all_documents(str(docs_dir))

        results = retrieve_documents("ログイン方法", n_results=3)
        assert isinstance(results, list)
        assert len(results) > 0

    def test_retrieve_documents_result_structure(self, tmp_path: Path):
        """検索結果が正しい構造を持つこと"""
        from app.rag.document_loader import load_all_documents
        from app.rag.retriever import retrieve_documents

        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "contracts.md").write_text(
            "# 契約ガイド\n\n## 料金プラン\n\nスタンダードプランは月額1000円です。プレミアムプランは月額3000円です。",
            encoding="utf-8",
        )

        store = _make_ephemeral_store()
        VectorStore._instance = store

        load_all_documents(str(docs_dir))

        results = retrieve_documents("料金プラン", n_results=1)
        assert len(results) > 0
        doc = results[0]
        assert "content" in doc
        assert "metadata" in doc
        assert "relevance_score" in doc
        assert "id" in doc
        assert isinstance(doc["content"], str)
        assert 0.0 <= doc["relevance_score"] <= 1.0


# ---------------------------------------------------------------------------
# 3. ChatService の結合テスト（エージェントはモック）
# ---------------------------------------------------------------------------


class TestChatServiceIntegration:
    """ChatService の結合テスト"""

    async def test_start_chat_returns_thread_id(self):
        """start_chat が非空の thread_id を返すこと"""
        from app.services.chat_service import ChatService

        service = ChatService()

        with patch.object(service, "_run_agent", new_callable=AsyncMock):
            thread_id = await service.start_chat(message="テスト質問")

        assert isinstance(thread_id, str)
        assert len(thread_id) > 0

    async def test_start_chat_creates_queue(self):
        """start_chat 後にキューが作成されること"""
        from app.services.chat_service import ChatService

        service = ChatService()

        with patch.object(service, "_run_agent", new_callable=AsyncMock):
            thread_id = await service.start_chat(message="テスト")

        assert thread_id in service._queues

    async def test_start_chat_with_custom_thread_id(self):
        """カスタム thread_id を指定した場合、そのIDが使われること"""
        from app.services.chat_service import ChatService

        service = ChatService()
        custom_id = f"custom-{uuid.uuid4().hex}"

        with patch.object(service, "_run_agent", new_callable=AsyncMock):
            returned_id = await service.start_chat(
                message="テスト",
                thread_id=custom_id,
            )

        assert returned_id == custom_id
        assert custom_id in service._queues

    async def test_start_chat_creates_background_task(self):
        """start_chat がバックグラウンドタスクを作成すること"""
        from app.services.chat_service import ChatService

        service = ChatService()

        with patch.object(service, "_run_agent", new_callable=AsyncMock):
            thread_id = await service.start_chat(message="テスト")

        assert thread_id in service._tasks
        assert isinstance(service._tasks[thread_id], asyncio.Task)
        # タスクをキャンセルしてクリーンアップ
        service._tasks[thread_id].cancel()
        await asyncio.sleep(0)

    async def test_queue_receives_events_from_run_agent(self):
        """_run_agent がキューにイベントを送出すること（モック）"""
        from app.services.chat_service import ChatService

        service = ChatService()

        async def mock_run_agent(thread_id, message, queue):
            await queue.put(StreamEvent(
                type=StreamEventType.TOKEN,
                content="テスト回答",
            ))
            await queue.put(StreamEvent(type=StreamEventType.DONE))

        with patch.object(service, "_run_agent", side_effect=mock_run_agent):
            thread_id = await service.start_chat(message="テスト")

        # タスク完了を待機
        await asyncio.sleep(0.1)

        queue = service._queues[thread_id]
        events = []
        while not queue.empty():
            events.append(await queue.get())

        event_types = [e.type for e in events]
        assert StreamEventType.TOKEN in event_types
        assert StreamEventType.DONE in event_types

    async def test_resume_chat_creates_task(self):
        """resume_chat がバックグラウンドタスクを作成すること"""
        from app.services.chat_service import ChatService

        service = ChatService()
        thread_id = "resume-test-thread"
        service.get_or_create_queue(thread_id)

        with patch.object(service, "_resume_agent", new_callable=AsyncMock):
            await service.resume_chat(
                thread_id=thread_id,
                response="技術サポート",
            )

        assert thread_id in service._tasks
        # タスクをクリーンアップ
        service._tasks[thread_id].cancel()
        await asyncio.sleep(0)

    async def test_cleanup_removes_queue_and_cancels_task(self):
        """cleanup がキューを削除しタスクをキャンセルすること"""
        from app.services.chat_service import ChatService

        service = ChatService()
        thread_id = "cleanup-test-thread"
        service._queues[thread_id] = asyncio.Queue()

        async def long_running():
            await asyncio.sleep(100)

        task = asyncio.create_task(long_running())
        service._tasks[thread_id] = task

        service.cleanup(thread_id)

        assert thread_id not in service._queues
        assert thread_id not in service._tasks
        await asyncio.sleep(0)
        assert task.cancelled()

    async def test_cleanup_on_nonexistent_thread_does_not_raise(self):
        """存在しない thread_id に cleanup を呼んでもエラーにならないこと"""
        from app.services.chat_service import ChatService

        service = ChatService()
        # 例外が発生しないことを確認
        service.cleanup("nonexistent-thread-id")

    async def test_get_or_create_queue_idempotent(self):
        """同じ thread_id に対して同一キューが返ること"""
        from app.services.chat_service import ChatService

        service = ChatService()
        thread_id = "idempotent-test"

        queue1 = service.get_or_create_queue(thread_id)
        queue2 = service.get_or_create_queue(thread_id)

        assert queue1 is queue2


# ---------------------------------------------------------------------------
# 4. ストリームイベントのシリアライズテスト
# ---------------------------------------------------------------------------


class TestStreamEventSerialization:
    """StreamEvent のシリアライズ結合テスト"""

    def test_token_event_serializes_to_json(self):
        """TOKEN イベントが有効な JSON にシリアライズされること"""
        event = StreamEvent(type=StreamEventType.TOKEN, content="こんにちは")
        serialized = event.model_dump_json()
        parsed = json.loads(serialized)

        assert parsed["type"] == "token"
        assert parsed["content"] == "こんにちは"

    def test_done_event_serializes_to_json(self):
        """DONE イベントが有効な JSON にシリアライズされること"""
        event = StreamEvent(type=StreamEventType.DONE)
        serialized = event.model_dump_json()
        parsed = json.loads(serialized)

        assert parsed["type"] == "done"

    def test_error_event_serializes_to_json(self):
        """ERROR イベントが有効な JSON にシリアライズされること"""
        event = StreamEvent(
            type=StreamEventType.ERROR,
            content="エラーが発生しました",
        )
        serialized = event.model_dump_json()
        parsed = json.loads(serialized)

        assert parsed["type"] == "error"
        assert parsed["content"] == "エラーが発生しました"

    def test_hitl_request_event_serializes_to_json(self):
        """HITL_REQUEST イベントが有効な JSON にシリアライズされること"""
        event = StreamEvent(
            type=StreamEventType.HITL_REQUEST,
            request_id="req-001",
            question="カテゴリを選んでください",
            options=["技術サポート", "料金", "その他"],
            input_type="buttons",
        )
        serialized = event.model_dump_json()
        parsed = json.loads(serialized)

        assert parsed["type"] == "hitl_request"
        assert parsed["request_id"] == "req-001"
        assert parsed["question"] == "カテゴリを選んでください"
        assert parsed["options"] == ["技術サポート", "料金", "その他"]
        assert parsed["input_type"] == "buttons"

    def test_tool_start_event_serializes_to_json(self):
        """TOOL_START イベントが有効な JSON にシリアライズされること"""
        event = StreamEvent(
            type=StreamEventType.TOOL_START,
            tool_name="search_knowledge",
        )
        serialized = event.model_dump_json()
        parsed = json.loads(serialized)

        assert parsed["type"] == "tool_start"
        assert parsed["tool_name"] == "search_knowledge"

    def test_tool_end_event_serializes_to_json(self):
        """TOOL_END イベントが有効な JSON にシリアライズされること"""
        event = StreamEvent(
            type=StreamEventType.TOOL_END,
            tool_name="generate_answer",
        )
        serialized = event.model_dump_json()
        parsed = json.loads(serialized)

        assert parsed["type"] == "tool_end"
        assert parsed["tool_name"] == "generate_answer"

    def test_message_complete_event_serializes_to_json(self):
        """MESSAGE_COMPLETE イベントが有効な JSON にシリアライズされること"""
        event = StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,
            content="完全な回答テキスト",
        )
        serialized = event.model_dump_json()
        parsed = json.loads(serialized)

        assert parsed["type"] == "message_complete"
        assert parsed["content"] == "完全な回答テキスト"

    def test_all_event_types_have_type_field(self):
        """すべてのイベントタイプが type フィールドを持つこと"""
        events = [
            StreamEvent(type=StreamEventType.TOKEN, content="test"),
            StreamEvent(type=StreamEventType.DONE),
            StreamEvent(type=StreamEventType.ERROR, content="err"),
            StreamEvent(
                type=StreamEventType.HITL_REQUEST,
                request_id="r",
                question="q",
                input_type="text",
            ),
            StreamEvent(type=StreamEventType.TOOL_START, tool_name="tool"),
            StreamEvent(type=StreamEventType.TOOL_END, tool_name="tool"),
            StreamEvent(type=StreamEventType.MESSAGE_COMPLETE, content="msg"),
        ]
        for event in events:
            parsed = json.loads(event.model_dump_json())
            assert "type" in parsed

    def test_optional_fields_are_none_by_default(self):
        """オプションフィールドがデフォルトで None であること"""
        event = StreamEvent(type=StreamEventType.DONE)
        assert event.content is None
        assert event.request_id is None
        assert event.question is None
        assert event.options is None
        assert event.input_type is None
        assert event.tool_name is None

    def test_event_type_enum_values(self):
        """StreamEventType の enum 値が正しい文字列であること"""
        assert StreamEventType.TOKEN == "token"
        assert StreamEventType.DONE == "done"
        assert StreamEventType.ERROR == "error"
        assert StreamEventType.HITL_REQUEST == "hitl_request"
        assert StreamEventType.TOOL_START == "tool_start"
        assert StreamEventType.TOOL_END == "tool_end"
        assert StreamEventType.MESSAGE_COMPLETE == "message_complete"
