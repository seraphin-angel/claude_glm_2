"""CrossEncoderRerankerのスレッドセーフティテスト。"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock, patch

import pytest

from app.rag.retriever import CrossEncoderReranker


class TestCrossEncoderRerankerThreadSafety:
    """CrossEncoderRerankerのスレッドセーフティテスト。"""

    def setup_method(self) -> None:
        """各テストの前にシングルトンをリセット。"""
        CrossEncoderReranker.reset_instance()

    def teardown_method(self) -> None:
        """各テストの後にシングルトンをリセット。"""
        CrossEncoderReranker.reset_instance()

    def test_get_instance_returns_singleton(self) -> None:
        """get_instance()が常に同じインスタンスを返すことを確認。"""
        instance1 = CrossEncoderReranker.get_instance()
        instance2 = CrossEncoderReranker.get_instance()

        assert instance1 is instance2

    def test_concurrent_get_instance_returns_same_instance(self) -> None:
        """複数スレッドから同時にget_instance()を呼んでも同じインスタンスが返されること。"""
        num_threads = 100
        instances: list[CrossEncoderReranker | None] = [None] * num_threads
        barrier = threading.Barrier(num_threads)

        def get_instance_task(index: int) -> None:
            barrier.wait()  # 全スレッドが同時に開始するよう同期
            instances[index] = CrossEncoderReranker.get_instance()

        threads = [
            threading.Thread(target=get_instance_task, args=(i,))
            for i in range(num_threads)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 全てのインスタンスが同じであることを確認
        first_instance = instances[0]
        assert first_instance is not None
        for instance in instances:
            assert instance is first_instance

    def test_concurrent_get_instance_with_executor(self) -> None:
        """ThreadPoolExecutorを使用した並行アクセステスト。"""
        num_tasks = 50
        instances: list[CrossEncoderReranker] = []

        def get_instance_task() -> CrossEncoderReranker:
            return CrossEncoderReranker.get_instance()

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_instance_task) for _ in range(num_tasks)]
            for future in as_completed(futures):
                instances.append(future.result())

        # 全てのインスタンスが同じであることを確認
        first_instance = instances[0]
        for instance in instances:
            assert instance is first_instance

    def test_model_loaded_only_once_under_concurrency(self) -> None:
        """並行アクセス時、モデルのロードが1回だけ行われることを確認。"""
        # このテストは_load_modelが呼ばれた回数を追跡するため
        # モックまたはカウンターが必要だが、ここでは
        # シングルトンインスタンスが1つであることを確認することで
        # 間接的にモデルの重複ロード防止を確認
        num_threads = 20
        instances: list[CrossEncoderReranker | None] = [None] * num_threads
        barrier = threading.Barrier(num_threads)

        def get_instance_task(index: int) -> None:
            barrier.wait()
            instances[index] = CrossEncoderReranker.get_instance()

        threads = [
            threading.Thread(target=get_instance_task, args=(i,))
            for i in range(num_threads)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # シングルトンが正しく機能していれば、
        # モデルは1つのインスタンスにのみ紐づく
        unique_instances = set(id(inst) for inst in instances)
        assert len(unique_instances) == 1

    def test_no_race_condition_in_instance_creation(self) -> None:
        """インスタンス作成時のレースコンディションがないことを確認。

        スレッドセーフでない実装では、複数のスレッドが同時に
        `if cls._instance is None` を通過し、複数のインスタンスが
        作成される可能性がある。
        """
        creation_count = 0
        creation_lock = threading.Lock()
        num_threads = 100
        barrier = threading.Barrier(num_threads)

        # 元の__new__メソッドを保存
        original_new = CrossEncoderReranker.__new__

        def tracked_new(cls, *args, **kwargs):  # type: ignore
            """インスタンス作成を追跡する__new__のラッパー。"""
            nonlocal creation_count
            with creation_lock:
                creation_count += 1
            # 少し遅延を入れてレースコンディションを誘発しやすくする
            time.sleep(0.001)
            return original_new(cls)

        # パッチを適用
        with patch.object(CrossEncoderReranker, "__new__", tracked_new):
            instances: list[CrossEncoderReranker | None] = [None] * num_threads

            def get_instance_task(index: int) -> None:
                barrier.wait()
                instances[index] = CrossEncoderReranker.get_instance()

            threads = [
                threading.Thread(target=get_instance_task, args=(i,))
                for i in range(num_threads)
            ]

            for t in threads:
                t.start()
            for t in threads:
                t.join()

        # スレッドセーフな実装では、__new__は1回だけ呼ばれるべき
        # ダブルチェックロッキングがない場合、複数回呼ばれる可能性がある
        assert creation_count == 1, (
            f"Expected exactly 1 instance creation, but got {creation_count}. "
            "This indicates a race condition in singleton initialization."
        )


class TestCrossEncoderRerankerModelLoadFailure:
    """CrossEncoderRerankerのモデルロード失敗時のテスト（Criticality: 7-8）"""

    def setup_method(self) -> None:
        """各テストの前にシングルトンをリセット。"""
        CrossEncoderReranker.reset_instance()

    def teardown_method(self) -> None:
        """各テストの後にシングルトンをリセット。"""
        CrossEncoderReranker.reset_instance()

    def test_rerank_with_empty_documents(self) -> None:
        """空のドキュメントリストでリランキングを呼んでもエラーにならないこと。"""
        reranker = CrossEncoderReranker.get_instance()
        result = reranker.rerank("test query", [], top_k=5)
        assert result == []

    def test_model_load_failure_raises_exception(self) -> None:
        """モデルロード失敗時に例外が発生すること（現在の実装の確認）。"""
        reranker = CrossEncoderReranker.get_instance()

        # CrossEncoderのインポートで例外が発生するようにモック
        with patch.dict(
            "sys.modules",
            {"sentence_transformers": None},
        ):
            # モデルロードを試みると例外が発生する
            with pytest.raises(Exception):
                reranker._load_model()

    def test_rerank_returns_scored_documents(self) -> None:
        """リランキングがスコア付きドキュメントを返すこと（モデルありの場合）。"""
        reranker = CrossEncoderReranker.get_instance()

        # モデルをモック
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.9, 0.7, 0.5]

        with patch.object(reranker, "_load_model", return_value=mock_model):
            documents = [
                {"id": "1", "content": "Document 1", "metadata": {}},
                {"id": "2", "content": "Document 2", "metadata": {}},
                {"id": "3", "content": "Document 3", "metadata": {}},
            ]

            result = reranker.rerank("test query", documents, top_k=2)

            # top_kで切り詰められていること
            assert len(result) == 2
            # スコア順でソートされていること
            assert result[0]["rerank_score"] == 0.9
            assert result[1]["rerank_score"] == 0.7
            # 元のフィールドが保持されていること
            assert "id" in result[0]
            assert "content" in result[0]

    def test_rerank_preserves_document_fields(self) -> None:
        """リランキング結果が元のドキュメントのフィールドを保持すること。"""
        reranker = CrossEncoderReranker.get_instance()

        mock_model = MagicMock()
        mock_model.predict.return_value = [0.8]

        with patch.object(reranker, "_load_model", return_value=mock_model):
            documents = [
                {
                    "id": "doc-123",
                    "content": "Test content",
                    "metadata": {"source": "test", "page": 1},
                    "relevance_score": 0.5,
                },
            ]

            result = reranker.rerank("query", documents, top_k=5)

            assert len(result) == 1
            assert result[0]["id"] == "doc-123"
            assert result[0]["content"] == "Test content"
            assert result[0]["metadata"] == {"source": "test", "page": 1}
            assert result[0]["relevance_score"] == 0.5
            assert "rerank_score" in result[0]
