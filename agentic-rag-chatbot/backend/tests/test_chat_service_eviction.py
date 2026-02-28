"""Tests for ChatService LRU eviction behavior.

Critical Test Cases (Criticality 9-10):
- アクティブなタスクがあるスレッドがevictionされる場合のグレースフルキャンセル
- LRU evictionの正しい動作
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid


class TestChatServiceLRUEviction:
    """ChatServiceのLRU evictionテスト"""

    @pytest.mark.asyncio
    async def test_eviction_removes_oldest_thread(self):
        """LRU evictionが最も古いスレッドを削除すること"""
        from app.services.chat_service import ChatService

        # Arrange
        service = ChatService()
        thread_ids = []

        # MAX_CONCURRENT_THREADS + 1 個のスレッドを作成
        for i in range(service.MAX_CONCURRENT_THREADS + 1):
            tid = str(uuid.uuid4())
            thread_ids.append(tid)
            service.get_or_create_queue(tid)

        # Act & Assert: 最初のスレッドがevictionされていること
        assert thread_ids[0] not in service._queues
        assert len(service._queues) == service.MAX_CONCURRENT_THREADS

        # Cleanup
        for tid in thread_ids:
            service.cleanup(tid)

    @pytest.mark.asyncio
    async def test_eviction_with_active_task_cancels_gracefully(self):
        """アクティブなタスクがあるスレッドがevictionされる場合のグレースフルキャンセル"""
        from app.services.chat_service import ChatService

        # Arrange
        service = ChatService()
        oldest_thread_id = str(uuid.uuid4())

        # 最初のスレッドを作成（これがeviction対象になる）
        service.get_or_create_queue(oldest_thread_id)

        # アクティブなタスクを追加
        task_cancelled = False

        async def active_task():
            nonlocal task_cancelled
            try:
                await asyncio.sleep(100)
            except asyncio.CancelledError:
                task_cancelled = True
                raise

        task = asyncio.create_task(active_task())
        service._tasks[oldest_thread_id] = task

        # 少し待ってタスクが実行中であることを確認
        await asyncio.sleep(0.01)
        assert not task.done()

        # Act: MAX_CONCURRENT_THREADSに達するまで新しいスレッドを作成してevictionを誘発
        for i in range(service.MAX_CONCURRENT_THREADS):
            tid = str(uuid.uuid4())
            service.get_or_create_queue(tid)

        # Assert: 古いスレッドがevictionされ、タスクがキャンセルされていること
        await asyncio.sleep(0.05)  # キャンセルが処理されるのを待つ
        assert oldest_thread_id not in service._queues
        assert task.done()
        assert task_cancelled is True

        # Cleanup
        service._queues.clear()
        service._tasks.clear()

    @pytest.mark.asyncio
    async def test_eviction_cleanup_releases_all_resources(self):
        """eviction時に全リソースが解放されること"""
        from app.services.chat_service import ChatService

        # Arrange
        service = ChatService()
        oldest_thread_id = str(uuid.uuid4())

        # 最初のスレッドを作成
        service.get_or_create_queue(oldest_thread_id)
        service._tasks[oldest_thread_id] = asyncio.create_task(asyncio.sleep(100))

        # Act: evictionを誘発
        for i in range(service.MAX_CONCURRENT_THREADS):
            service.get_or_create_queue(str(uuid.uuid4()))

        # Assert: キューとタスクの両方が解放されていること
        assert oldest_thread_id not in service._queues
        assert oldest_thread_id not in service._tasks

        # Cleanup
        service._queues.clear()
        service._tasks.clear()

    @pytest.mark.asyncio
    async def test_eviction_order_is_fifo(self):
        """evictionの順序がFIFOであること"""
        from app.services.chat_service import ChatService

        # Arrange
        service = ChatService()
        thread_ids = []

        # 複数のスレッドを作成
        num_threads = 5
        for i in range(num_threads):
            tid = str(uuid.uuid4())
            thread_ids.append(tid)
            service.get_or_create_queue(tid)

        # Act: evictionを誘発
        for i in range(service.MAX_CONCURRENT_THREADS - num_threads + 1):
            service.get_or_create_queue(str(uuid.uuid4()))

        # Assert: 最初のスレッドがevictionされていること
        assert thread_ids[0] not in service._queues

        # Cleanup
        service._queues.clear()
        service._tasks.clear()

    @pytest.mark.asyncio
    async def test_no_eviction_when_below_limit(self):
        """制限以下の場合はevictionが発生しないこと"""
        from app.services.chat_service import ChatService

        # Arrange
        service = ChatService()
        thread_ids = []

        # 制限より少ないスレッドを作成
        num_threads = service.MAX_CONCURRENT_THREADS - 1
        for i in range(num_threads):
            tid = str(uuid.uuid4())
            thread_ids.append(tid)
            service.get_or_create_queue(tid)

        # Assert: 全スレッドが存在すること
        for tid in thread_ids:
            assert tid in service._queues

        # Cleanup
        for tid in thread_ids:
            service.cleanup(tid)


class TestChatServiceTaskCancellation:
    """タスクキャンセルのテスト"""

    @pytest.mark.asyncio
    async def test_cleanup_cancels_incomplete_task(self):
        """cleanupが未完了のタスクをキャンセルすること"""
        from app.services.chat_service import ChatService

        # Arrange
        service = ChatService()
        thread_id = str(uuid.uuid4())

        service.get_or_create_queue(thread_id)
        service._tasks[thread_id] = asyncio.create_task(asyncio.sleep(100))

        # Act
        service.cleanup(thread_id)

        # Assert
        assert thread_id not in service._tasks
        await asyncio.sleep(0.01)
        assert service._tasks.get(thread_id) is None

    @pytest.mark.asyncio
    async def test_cleanup_preserves_completed_task_status(self):
        """cleanupが完了したタスクの状態に影響しないこと"""
        from app.services.chat_service import ChatService

        # Arrange
        service = ChatService()
        thread_id = str(uuid.uuid4())

        service.get_or_create_queue(thread_id)
        task = asyncio.create_task(asyncio.sleep(0))  # 即座に完了
        service._tasks[thread_id] = task

        # タスクが完了するのを待つ
        await asyncio.sleep(0.01)

        # Act
        service.cleanup(thread_id)

        # Assert: タスクは完了状態のまま
        assert task.done()
        assert thread_id not in service._tasks

    @pytest.mark.asyncio
    async def test_multiple_tasks_cancellation(self):
        """複数のタスクがキャンセルされること"""
        from app.services.chat_service import ChatService

        # Arrange
        service = ChatService()
        thread_ids = []

        for i in range(5):
            tid = str(uuid.uuid4())
            thread_ids.append(tid)
            service.get_or_create_queue(tid)
            service._tasks[tid] = asyncio.create_task(asyncio.sleep(100))

        # Act
        for tid in thread_ids:
            service.cleanup(tid)

        # Assert
        await asyncio.sleep(0.01)
        assert len(service._tasks) == 0
        assert len(service._queues) == 0


class TestChatServiceEdgeCases:
    """エッジケースのテスト"""

    @pytest.mark.asyncio
    async def test_get_or_create_queue_returns_existing_queue(self):
        """get_or_create_queueが既存のキューを返すこと"""
        from app.services.chat_service import ChatService

        # Arrange
        service = ChatService()
        thread_id = str(uuid.uuid4())
        queue1 = service.get_or_create_queue(thread_id)

        # Act
        queue2 = service.get_or_create_queue(thread_id)

        # Assert
        assert queue1 is queue2

        # Cleanup
        service.cleanup(thread_id)

    @pytest.mark.asyncio
    async def test_concurrent_get_or_create_queue(self):
        """同時にget_or_create_queueを呼んでも安全であること"""
        from app.services.chat_service import ChatService

        # Arrange
        service = ChatService()
        thread_id = str(uuid.uuid4())

        # Act: 同時に複数のget_or_create_queueを呼ぶ
        results = await asyncio.gather(
            asyncio.to_thread(service.get_or_create_queue, thread_id),
            asyncio.to_thread(service.get_or_create_queue, thread_id),
            asyncio.to_thread(service.get_or_create_queue, thread_id),
        )

        # Assert: 全て同じキューを返すこと
        assert all(q is results[0] for q in results)

        # Cleanup
        service.cleanup(thread_id)

    @pytest.mark.asyncio
    async def test_eviction_with_no_task(self):
        """タスクがないスレッドのevictionが安全であること"""
        from app.services.chat_service import ChatService

        # Arrange
        service = ChatService()
        thread_ids = []

        # タスクなしでスレッドを作成
        for i in range(service.MAX_CONCURRENT_THREADS + 1):
            tid = str(uuid.uuid4())
            thread_ids.append(tid)
            service.get_or_create_queue(tid)
            # タスクは追加しない

        # Act & Assert: エラーが発生しないこと
        assert len(service._queues) == service.MAX_CONCURRENT_THREADS

        # Cleanup
        service._queues.clear()
