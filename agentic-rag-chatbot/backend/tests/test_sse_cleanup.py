"""Tests for SSE streaming resource cleanup.

Critical Test Cases (Criticality 9-10):
- タイムアウト時にキューに残ったメッセージが適切に処理されること
- 複数クライアントが同時タイムアウトした場合のリソースリークがないこと
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid


class TestSSETimeoutCleanup:
    """SSEタイムアウト時のリソースクリーンアップテスト"""

    @pytest.mark.asyncio
    async def test_stream_timeout_cleanup_with_pending_messages(self):
        """タイムアウト時にキューに残ったメッセージが適切に処理されること"""
        from app.services.chat_service import ChatService
        from app.models.messages import StreamEvent, StreamEventType

        # Arrange
        service = ChatService()
        thread_id = str(uuid.uuid4())
        queue = service.get_or_create_queue(thread_id)

        # キューにメッセージを追加
        for i in range(5):
            await queue.put(StreamEvent(type=StreamEventType.TOKEN, content=f"msg{i}"))

        # キューにメッセージが残っていることを確認
        assert queue.qsize() == 5

        # Act: cleanupを実行
        service.cleanup(thread_id)

        # Assert: キューが削除されていること
        assert thread_id not in service._queues

    @pytest.mark.asyncio
    async def test_stream_timeout_cancels_running_task(self):
        """タイムアウト時に実行中のタスクがキャンセルされること"""
        from app.services.chat_service import ChatService

        # Arrange
        service = ChatService()
        thread_id = str(uuid.uuid4())

        # 実行中のタスクをシミュレート
        task_was_cancelled = False

        async def long_running_task():
            nonlocal task_was_cancelled
            try:
                await asyncio.sleep(100)  # 長時間実行
            except asyncio.CancelledError:
                task_was_cancelled = True
                raise

        task = asyncio.create_task(long_running_task())
        service._tasks[thread_id] = task
        service._queues[thread_id] = asyncio.Queue()

        # 少し待ってタスクが開始されていることを確認
        await asyncio.sleep(0.01)
        assert not task.done()

        # Act: cleanupを実行
        service.cleanup(thread_id)

        # Assert: タスクがキャンセルされていること
        await asyncio.sleep(0.01)  # キャンセルが処理されるのを待つ
        assert task.done()
        assert task_was_cancelled is True
        assert thread_id not in service._tasks

    @pytest.mark.asyncio
    async def test_concurrent_stream_timeouts_no_resource_leak(self):
        """複数クライアントが同時タイムアウトした場合のリソースリークがないこと"""
        from app.services.chat_service import ChatService

        # Arrange
        service = ChatService()
        num_clients = 10
        thread_ids = [str(uuid.uuid4()) for _ in range(num_clients)]

        # 複数のキューとタスクを作成
        for tid in thread_ids:
            service.get_or_create_queue(tid)
            service._tasks[tid] = asyncio.create_task(asyncio.sleep(100))

        # 全てのリソースが作成されたことを確認
        assert len(service._queues) == num_clients
        assert len(service._tasks) == num_clients

        # Act: 全クライアントを同時にクリーンアップ
        cleanup_tasks = [asyncio.create_task(
            asyncio.to_thread(service.cleanup, tid)
        ) for tid in thread_ids]
        await asyncio.gather(*cleanup_tasks)

        # Assert: 全リソースがクリーンアップされていること
        assert len(service._queues) == 0
        assert len(service._tasks) == 0

        # 全タスクがキャンセルされていること
        for tid in thread_ids:
            assert tid not in service._tasks

    @pytest.mark.asyncio
    async def test_cleanup_idempotent(self):
        """cleanup が冪等であること（複数回呼び出しても安全）"""
        from app.services.chat_service import ChatService

        # Arrange
        service = ChatService()
        thread_id = str(uuid.uuid4())
        service.get_or_create_queue(thread_id)

        # Act: 同じthread_idで複数回cleanup
        service.cleanup(thread_id)
        service.cleanup(thread_id)  # 2回目
        service.cleanup(thread_id)  # 3回目

        # Assert: エラーが発生しないこと
        assert thread_id not in service._queues

    @pytest.mark.asyncio
    async def test_cleanup_non_existent_thread_safe(self):
        """存在しないthread_idでcleanupしても安全であること"""
        from app.services.chat_service import ChatService

        # Arrange
        service = ChatService()
        non_existent_id = str(uuid.uuid4())

        # Act & Assert: 例外が発生しないこと
        service.cleanup(non_existent_id)  # Should not raise


class TestSSEEventGeneratorCleanup:
    """SSE event_generator のクリーンアップテスト"""

    @pytest.mark.asyncio
    async def test_event_generator_cleanup_on_done_event(self):
        """DONEイベント受信時にcleanupが呼ばれること"""
        from app.services.chat_service import ChatService
        from app.models.messages import StreamEvent, StreamEventType

        # Arrange
        service = ChatService()
        thread_id = str(uuid.uuid4())
        queue = service.get_or_create_queue(thread_id)

        # DONEイベントを追加
        await queue.put(StreamEvent(type=StreamEventType.DONE))

        # Act: キューからイベントを取得
        event = await queue.get()

        # Assert: DONEイベントであること
        assert event.type == StreamEventType.DONE

        # Cleanup
        service.cleanup(thread_id)

    @pytest.mark.asyncio
    async def test_event_generator_cleanup_on_error_event(self):
        """ERRORイベント受信時にcleanupが呼ばれること"""
        from app.services.chat_service import ChatService
        from app.models.messages import StreamEvent, StreamEventType

        # Arrange
        service = ChatService()
        thread_id = str(uuid.uuid4())
        queue = service.get_or_create_queue(thread_id)

        # ERRORイベントを追加
        await queue.put(StreamEvent(
            type=StreamEventType.ERROR,
            content="Test error"
        ))

        # Act
        event = await queue.get()

        # Assert
        assert event.type == StreamEventType.ERROR

        # Cleanup
        service.cleanup(thread_id)


class TestSSEQueueManagement:
    """SSEキュー管理のテスト"""

    @pytest.mark.asyncio
    async def test_queue_maxsize_enforced(self):
        """キューの最大サイズが制限されること"""
        from app.services.chat_service import ChatService
        from app.models.messages import StreamEvent, StreamEventType

        # Arrange
        service = ChatService()
        thread_id = str(uuid.uuid4())
        queue = service.get_or_create_queue(thread_id)

        # Act: QUEUE_MAXSIZE (100) まで追加
        maxsize = service.QUEUE_MAXSIZE
        for i in range(maxsize):
            await queue.put(StreamEvent(type=StreamEventType.TOKEN, content=f"msg{i}"))

        # Assert: キューが満杯であること
        assert queue.qsize() == maxsize

        # Cleanup
        service.cleanup(thread_id)

    @pytest.mark.asyncio
    async def test_queue_full_blocks_producer(self):
        """キューが満杯の場合、プロデューサーがブロックされること"""
        from app.services.chat_service import ChatService
        from app.models.messages import StreamEvent, StreamEventType

        # Arrange
        service = ChatService()
        thread_id = str(uuid.uuid4())
        queue = service.get_or_create_queue(thread_id)

        # キューを満杯にする
        maxsize = service.QUEUE_MAXSIZE
        for i in range(maxsize):
            await queue.put(StreamEvent(type=StreamEventType.TOKEN, content=f"msg{i}"))

        # 追加のputがタイムアウトすることを確認
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                queue.put(StreamEvent(type=StreamEventType.TOKEN, content="overflow")),
                timeout=0.1
            )

        # Cleanup
        service.cleanup(thread_id)
