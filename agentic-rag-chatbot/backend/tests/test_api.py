"""FastAPI エンドポイントのテスト"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.main import app
from app.models.messages import StreamEvent, StreamEventType

TEST_THREAD_UUID = "550e8400-e29b-41d4-a716-446655440000"


# ---------------------------------------------------------------------------
# GET /api/health テスト
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    async def test_health_returns_200(self, client: AsyncClient):
        """GET /api/health が 200 を返すこと"""
        response = await client.get("/api/health")
        assert response.status_code == 200

    async def test_health_response_structure(self, client: AsyncClient):
        """GET /api/health が正しいJSON構造を返すこと"""
        response = await client.get("/api/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
        assert "version" in data

    async def test_health_version_is_string(self, client: AsyncClient):
        """version フィールドが文字列であること"""
        response = await client.get("/api/health")
        data = response.json()
        assert isinstance(data["version"], str)


# ---------------------------------------------------------------------------
# POST /api/chat テスト
# ---------------------------------------------------------------------------


class TestStartChatEndpoint:
    async def test_start_chat_success(self, client: AsyncClient, auth_headers: dict):
        """POST /api/chat が正常なレスポンスを返すこと"""
        mock_service = MagicMock()
        mock_service.start_chat = AsyncMock(return_value="test-thread-id")

        with patch("app.api.chat.get_chat_service", return_value=mock_service):
            response = await client.post(
                "/api/chat",
                json={"message": "テストメッセージ"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["thread_id"] == "test-thread-id"
        assert data["data"]["status"] == "streaming"

    async def test_start_chat_with_thread_id(self, client: AsyncClient, auth_headers: dict):
        """既存 thread_id を指定したPOSTが正常に動作すること"""
        existing_thread = TEST_THREAD_UUID
        mock_service = MagicMock()
        mock_service.start_chat = AsyncMock(return_value=existing_thread)

        with patch("app.api.chat.get_chat_service", return_value=mock_service):
            response = await client.post(
                "/api/chat",
                json={"message": "続きの質問", "thread_id": existing_thread},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["thread_id"] == existing_thread
        mock_service.start_chat.assert_called_once_with(
            message="続きの質問",
            thread_id=existing_thread,
            image_data=None,
        )

    async def test_start_chat_empty_message_returns_422(self, client: AsyncClient, auth_headers: dict):
        """空メッセージでバリデーションエラー (422) が返ること"""
        response = await client.post(
            "/api/chat",
            json={"message": ""},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_start_chat_missing_message_returns_422(self, client: AsyncClient, auth_headers: dict):
        """message フィールドなしで 422 が返ること"""
        response = await client.post(
            "/api/chat",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_start_chat_message_too_long_returns_422(self, client: AsyncClient, auth_headers: dict):
        """2001文字のメッセージで 422 が返ること"""
        response = await client.post(
            "/api/chat",
            json={"message": "a" * 2001},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_start_chat_calls_service_with_correct_args(self, client: AsyncClient, auth_headers: dict):
        """サービスが正しい引数で呼び出されること"""
        mock_service = MagicMock()
        mock_service.start_chat = AsyncMock(return_value="new-thread-id")

        with patch("app.api.chat.get_chat_service", return_value=mock_service):
            await client.post(
                "/api/chat",
                json={"message": "こんにちは"},
                headers=auth_headers,
            )

        mock_service.start_chat.assert_called_once_with(
            message="こんにちは",
            thread_id=None,
            image_data=None,
        )

    async def test_start_chat_invalid_thread_id_returns_422(self, client: AsyncClient, auth_headers: dict):
        """不正な thread_id 形式で 422 が返ること"""
        response = await client.post(
            "/api/chat",
            json={"message": "テスト", "thread_id": "not-a-uuid"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_start_chat_no_auth_returns_401(self, client: AsyncClient):
        """認証なしで 401 が返ること"""
        response = await client.post(
            "/api/chat",
            json={"message": "テスト"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/chat/stream/{thread_id} テスト
# ---------------------------------------------------------------------------


class TestStreamChatEndpoint:
    async def test_stream_returns_sse_content_type(self, client: AsyncClient, auth_headers: dict):
        """SSE エンドポイントが text/event-stream を返すこと"""
        queue: asyncio.Queue = asyncio.Queue()
        await queue.put(StreamEvent(type=StreamEventType.DONE))

        mock_service = MagicMock()
        mock_service.get_or_create_queue = MagicMock(return_value=queue)

        with patch("app.api.chat.get_chat_service", return_value=mock_service):
            response = await client.get(
                f"/api/chat/stream/{TEST_THREAD_UUID}",
                headers=auth_headers,
            )

        assert "text/event-stream" in response.headers.get("content-type", "")

    async def test_stream_returns_token_events(self, client: AsyncClient, auth_headers: dict):
        """TOKEN イベントがSSEストリームとして返されること"""
        queue: asyncio.Queue = asyncio.Queue()
        await queue.put(StreamEvent(type=StreamEventType.TOKEN, content="こんにちは"))
        await queue.put(StreamEvent(type=StreamEventType.DONE))

        mock_service = MagicMock()
        mock_service.get_or_create_queue = MagicMock(return_value=queue)

        with patch("app.api.chat.get_chat_service", return_value=mock_service):
            response = await client.get(
                f"/api/chat/stream/{TEST_THREAD_UUID}",
                headers=auth_headers,
            )

        body = response.text
        assert "token" in body
        assert "こんにちは" in body

    async def test_stream_terminates_on_done(self, client: AsyncClient, auth_headers: dict):
        """DONE イベントでストリームが終了すること"""
        queue: asyncio.Queue = asyncio.Queue()
        await queue.put(StreamEvent(type=StreamEventType.TOKEN, content="テスト"))
        await queue.put(StreamEvent(type=StreamEventType.DONE))

        mock_service = MagicMock()
        mock_service.get_or_create_queue = MagicMock(return_value=queue)

        with patch("app.api.chat.get_chat_service", return_value=mock_service):
            response = await client.get(
                f"/api/chat/stream/{TEST_THREAD_UUID}",
                headers=auth_headers,
            )

        assert response.status_code == 200
        lines = [line for line in response.text.split("\n") if line.startswith("data:")]
        assert len(lines) == 2  # TOKEN + DONE

    async def test_stream_terminates_on_error(self, client: AsyncClient, auth_headers: dict):
        """ERROR イベントでストリームが終了すること"""
        queue: asyncio.Queue = asyncio.Queue()
        await queue.put(StreamEvent(
            type=StreamEventType.ERROR,
            content="エラーが発生しました",
        ))

        mock_service = MagicMock()
        mock_service.get_or_create_queue = MagicMock(return_value=queue)

        with patch("app.api.chat.get_chat_service", return_value=mock_service):
            response = await client.get(
                f"/api/chat/stream/{TEST_THREAD_UUID}",
                headers=auth_headers,
            )

        assert response.status_code == 200
        assert "error" in response.text

    async def test_stream_includes_sse_headers(self, client: AsyncClient, auth_headers: dict):
        """SSEに必要なHTTPヘッダーが含まれること"""
        queue: asyncio.Queue = asyncio.Queue()
        await queue.put(StreamEvent(type=StreamEventType.DONE))

        mock_service = MagicMock()
        mock_service.get_or_create_queue = MagicMock(return_value=queue)

        with patch("app.api.chat.get_chat_service", return_value=mock_service):
            response = await client.get(
                f"/api/chat/stream/{TEST_THREAD_UUID}",
                headers=auth_headers,
            )

        assert response.headers.get("cache-control") == "no-cache"
        assert response.headers.get("x-accel-buffering") == "no"

    async def test_stream_data_is_valid_json(self, client: AsyncClient, auth_headers: dict):
        """SSEのdata行が有効なJSONであること"""
        queue: asyncio.Queue = asyncio.Queue()
        await queue.put(StreamEvent(type=StreamEventType.TOKEN, content="テスト"))
        await queue.put(StreamEvent(type=StreamEventType.DONE))

        mock_service = MagicMock()
        mock_service.get_or_create_queue = MagicMock(return_value=queue)

        with patch("app.api.chat.get_chat_service", return_value=mock_service):
            response = await client.get(
                f"/api/chat/stream/{TEST_THREAD_UUID}",
                headers=auth_headers,
            )

        data_lines = [line for line in response.text.split("\n") if line.startswith("data:")]
        for line in data_lines:
            json_str = line[len("data: "):]
            parsed = json.loads(json_str)
            assert "type" in parsed

    async def test_stream_hitl_event(self, client: AsyncClient, auth_headers: dict):
        """HITL_REQUEST イベントが正しくストリームされること"""
        queue: asyncio.Queue = asyncio.Queue()
        await queue.put(StreamEvent(
            type=StreamEventType.HITL_REQUEST,
            request_id="req-001",
            question="カテゴリを選んでください",
            options=["A", "B"],
            input_type="buttons",
        ))
        await queue.put(StreamEvent(type=StreamEventType.DONE))

        mock_service = MagicMock()
        mock_service.get_or_create_queue = MagicMock(return_value=queue)

        with patch("app.api.chat.get_chat_service", return_value=mock_service):
            response = await client.get(
                f"/api/chat/stream/{TEST_THREAD_UUID}",
                headers=auth_headers,
            )

        assert "hitl_request" in response.text
        assert "req-001" in response.text

    async def test_stream_cleanup_called_after_done(self, client: AsyncClient, auth_headers: dict):
        """ストリーム終了後にcleanupが呼ばれること"""
        queue: asyncio.Queue = asyncio.Queue()
        await queue.put(StreamEvent(type=StreamEventType.DONE))

        mock_service = MagicMock()
        mock_service.get_or_create_queue = MagicMock(return_value=queue)
        mock_service.cleanup = MagicMock()

        with patch("app.api.chat.get_chat_service", return_value=mock_service):
            await client.get(
                f"/api/chat/stream/{TEST_THREAD_UUID}",
                headers=auth_headers,
            )

        mock_service.cleanup.assert_called_once_with(TEST_THREAD_UUID)

    async def test_stream_invalid_uuid_returns_422(self, client: AsyncClient, auth_headers: dict):
        """不正な thread_id 形式で 422 が返ること"""
        response = await client.get(
            "/api/chat/stream/not-a-valid-uuid",
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_stream_no_auth_returns_401(self, client: AsyncClient):
        """認証なしで 401 が返ること"""
        response = await client.get(f"/api/chat/stream/{TEST_THREAD_UUID}")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/chat/resume/{thread_id} テスト
# ---------------------------------------------------------------------------


class TestResumeChatEndpoint:
    async def test_resume_success(self, client: AsyncClient, auth_headers: dict):
        """POST /api/chat/resume/{thread_id} が正常に動作すること"""
        mock_service = MagicMock()
        mock_service.resume_chat = AsyncMock()
        mock_service._queues = {TEST_THREAD_UUID: MagicMock()}

        with patch("app.api.chat.get_chat_service", return_value=mock_service):
            response = await client.post(
                f"/api/chat/resume/{TEST_THREAD_UUID}",
                json={"request_id": "req-001", "response": "はい"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["thread_id"] == TEST_THREAD_UUID
        assert data["data"]["status"] == "streaming"

    async def test_resume_calls_service_with_response(self, client: AsyncClient, auth_headers: dict):
        """resume_chat がユーザー回答付きで呼ばれること"""
        mock_service = MagicMock()
        mock_service.resume_chat = AsyncMock()
        mock_service._queues = {TEST_THREAD_UUID: MagicMock()}

        with patch("app.api.chat.get_chat_service", return_value=mock_service):
            await client.post(
                f"/api/chat/resume/{TEST_THREAD_UUID}",
                json={"request_id": "req-abc", "response": "技術サポート"},
                headers=auth_headers,
            )

        mock_service.resume_chat.assert_called_once_with(
            thread_id=TEST_THREAD_UUID,
            response="技術サポート",
        )

    async def test_resume_creates_queue_if_missing(self, client: AsyncClient, auth_headers: dict):
        """キューが存在しない場合に作成されること"""
        mock_service = MagicMock()
        mock_service.resume_chat = AsyncMock()
        mock_service._queues = {}  # 空のキュー
        mock_service.get_or_create_queue = MagicMock()

        with patch("app.api.chat.get_chat_service", return_value=mock_service):
            response = await client.post(
                f"/api/chat/resume/{TEST_THREAD_UUID}",
                json={"request_id": "req-001", "response": "テスト"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        mock_service.get_or_create_queue.assert_called_once_with(TEST_THREAD_UUID)

    async def test_resume_empty_response_returns_422(self, client: AsyncClient, auth_headers: dict):
        """空の response で 422 が返ること"""
        response = await client.post(
            f"/api/chat/resume/{TEST_THREAD_UUID}",
            json={"request_id": "req-001", "response": ""},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_resume_missing_fields_returns_422(self, client: AsyncClient, auth_headers: dict):
        """必須フィールドなしで 422 が返ること"""
        response = await client.post(
            f"/api/chat/resume/{TEST_THREAD_UUID}",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_resume_invalid_uuid_returns_422(self, client: AsyncClient, auth_headers: dict):
        """不正な thread_id 形式で 422 が返ること"""
        response = await client.post(
            "/api/chat/resume/not-a-valid-uuid",
            json={"request_id": "req-001", "response": "テスト"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_resume_no_auth_returns_401(self, client: AsyncClient):
        """認証なしで 401 が返ること"""
        response = await client.post(
            f"/api/chat/resume/{TEST_THREAD_UUID}",
            json={"request_id": "req-001", "response": "テスト"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# ChatService ユニットテスト
# ---------------------------------------------------------------------------


class TestChatService:
    async def test_get_or_create_queue_creates_new(self):
        """新しいthread_idでキューが作成されること"""
        from app.services.chat_service import ChatService

        service = ChatService()
        queue = service.get_or_create_queue("new-thread")
        assert isinstance(queue, asyncio.Queue)

    async def test_get_or_create_queue_returns_existing(self):
        """同じthread_idで同じキューが返されること"""
        from app.services.chat_service import ChatService

        service = ChatService()
        queue1 = service.get_or_create_queue("same-thread")
        queue2 = service.get_or_create_queue("same-thread")
        assert queue1 is queue2

    async def test_cleanup_removes_queue_and_task(self):
        """cleanup がキューとタスクを削除すること"""
        from app.services.chat_service import ChatService

        service = ChatService()
        service._queues["t-001"] = asyncio.Queue()

        async def dummy():
            await asyncio.sleep(10)

        task = asyncio.create_task(dummy())
        service._tasks["t-001"] = task

        service.cleanup("t-001")

        assert "t-001" not in service._queues
        assert "t-001" not in service._tasks
        # cancel() を呼んだ直後はまだ cancelling 状態なので、
        # イベントループに制御を渡してから確認する
        await asyncio.sleep(0)
        assert task.cancelled()

    async def test_start_chat_returns_thread_id(self):
        """start_chat が thread_id を返すこと"""
        from app.services.chat_service import ChatService

        service = ChatService()

        with patch.object(service, "_run_agent", new_callable=AsyncMock):
            thread_id = await service.start_chat(message="テスト")

        assert isinstance(thread_id, str)
        assert len(thread_id) > 0

    async def test_start_chat_uses_provided_thread_id(self):
        """start_chat に thread_id を渡すと同じIDが返ること"""
        from app.services.chat_service import ChatService

        service = ChatService()
        custom_id = "custom-thread-id"

        with patch.object(service, "_run_agent", new_callable=AsyncMock):
            thread_id = await service.start_chat(message="テスト", thread_id=custom_id)

        assert thread_id == custom_id

    async def test_get_chat_service_returns_singleton(self):
        """get_chat_service がシングルトンを返すこと"""
        import app.services.chat_service as cs_module
        from app.services.chat_service import get_chat_service

        # シングルトンをリセット
        cs_module._chat_service = None

        service1 = get_chat_service()
        service2 = get_chat_service()
        assert service1 is service2

        # クリーンアップ
        cs_module._chat_service = None

    async def test_error_response_hides_internal_details(self):
        """エラーレスポンスに内部情報が含まれないこと"""
        import os
        from app.services.chat_service import ChatService

        service = ChatService()
        queue = service.get_or_create_queue("err-thread")

        # DEBUG_MODE が false の場合
        os.environ.pop("DEBUG_MODE", None)

        with patch("app.agents.agent.get_agent", new_callable=AsyncMock) as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.astream_events = AsyncMock(side_effect=RuntimeError("Internal DB connection failed at host:5432"))
            mock_get_agent.return_value = mock_agent

            await service._run_agent("err-thread", "テスト", queue, None)

        events = []
        while not queue.empty():
            events.append(await queue.get())

        error_events = [e for e in events if e.type == StreamEventType.ERROR]
        assert len(error_events) == 1
        assert "5432" not in error_events[0].content
        assert "Internal DB" not in error_events[0].content
        assert "エラーが発生しました" in error_events[0].content

    async def test_max_steps_exceeded_sends_error(self):
        """MAX_STEPS を超えた場合にエラーイベントが送出されること"""
        from app.services.chat_service import ChatService

        service = ChatService()
        service.MAX_STEPS = 3  # テスト用に低く設定
        queue = service.get_or_create_queue("step-thread")

        # on_tool_end イベントを MAX_STEPS 回以上生成するモックエージェント
        events = []
        for i in range(5):
            events.append({"event": "on_tool_start", "name": f"tool_{i}", "data": {}})
            events.append({"event": "on_tool_end", "name": f"tool_{i}", "data": {}})

        async def mock_astream_events(*args, **kwargs):
            for event in events:
                yield event

        with patch("app.agents.agent.get_agent", new_callable=AsyncMock) as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.astream_events = mock_astream_events
            mock_get_agent.return_value = mock_agent

            await service._run_agent("step-thread", "テスト", queue, None)

        collected = []
        while not queue.empty():
            collected.append(await queue.get())

        error_events = [e for e in collected if e.type == StreamEventType.ERROR]
        assert len(error_events) == 1
        assert "上限" in error_events[0].content

        # TOOL_END イベントは MAX_STEPS (3) 個までしか送出されないこと
        tool_end_events = [e for e in collected if e.type == StreamEventType.TOOL_END]
        assert len(tool_end_events) == 3

    async def test_queue_eviction_when_max_reached(self):
        """MAX_CONCURRENT_THREADS を超えた場合にLRU evictionが行われること"""
        from app.services.chat_service import ChatService

        service = ChatService()
        service.MAX_CONCURRENT_THREADS = 3

        service.get_or_create_queue("thread-1")
        service.get_or_create_queue("thread-2")
        service.get_or_create_queue("thread-3")
        assert len(service._queues) == 3

        service.get_or_create_queue("thread-4")
        assert len(service._queues) == 3
        assert "thread-1" not in service._queues
        assert "thread-4" in service._queues

    async def test_exception_handling_uses_type_check_for_graph_interrupt(self):
        """GraphInterrupt例外を型チェックで判定し、適切にログ出力すること"""
        from app.services.chat_service import ChatService
        from langgraph.errors import GraphInterrupt

        service = ChatService()
        queue = service.get_or_create_queue("interrupt-thread")
        config = {"configurable": {"thread_id": "interrupt-thread"}}

        # GraphInterrupt を送出する非同期ジェネレーター
        async def mock_astream_events(*args, **kwargs):
            raise GraphInterrupt("User interrupted")
            yield  # ジェネレーターにするため

        with patch("app.agents.agent.get_agent", new_callable=AsyncMock) as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.astream_events = mock_astream_events
            mock_agent.get_state = MagicMock(return_value=MagicMock(tasks=[]))
            mock_get_agent.return_value = mock_agent

            await service._run_agent("interrupt-thread", "テスト", queue, None)

        # HITL_REQUEST イベントが送出されること（interrupt として処理）
        events = []
        while not queue.empty():
            events.append(await queue.get())

        hitl_events = [e for e in events if e.type == StreamEventType.HITL_REQUEST]
        assert len(hitl_events) == 1

    async def test_non_interrupt_exception_logs_with_error_id(self):
        """GraphInterrupt以外の例外でエラーID付きログが出力されること"""
        import os
        from app.services.chat_service import ChatService

        service = ChatService()
        queue = service.get_or_create_queue("error-thread")

        os.environ.pop("DEBUG_MODE", None)

        with patch("app.agents.agent.get_agent", new_callable=AsyncMock) as mock_get_agent, \
             patch("app.services.chat_service.logger") as mock_logger:
            mock_agent = MagicMock()
            # 通常の例外を送出
            mock_agent.astream_events = AsyncMock(side_effect=RuntimeError("Some error"))
            mock_get_agent.return_value = mock_agent

            await service._run_agent("error-thread", "テスト", queue, None)

        # logger.error が呼ばれ、error_id が含まれていることを確認
        assert mock_logger.error.called
        error_call = mock_logger.error.call_args
        assert "error_id" in error_call[1]
        assert error_call[1].get("exc_info") is True
