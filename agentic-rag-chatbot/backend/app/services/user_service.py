"""P3-54: パーソナライゼーション - ユーザーサービス（CRUD管理）"""

from datetime import datetime, timezone
from threading import Lock
from typing import Optional

from app.models.user import (
    ConversationRecord,
    UserCreateRequest,
    UserPlan,
    UserProfile,
)


class UserService:
    """ユーザーのCRUD管理サービス（インメモリ実装）"""

    _instance: Optional["UserService"] = None
    _lock: Lock = Lock()

    def __init__(self) -> None:
        # ユーザーIDをキーとする不変辞書として管理
        self._users: dict[str, UserProfile] = {}
        # インスタンスレベルのデータロック（書き込み操作用）
        self._data_lock: Lock = Lock()

    @classmethod
    def get_instance(cls) -> "UserService":
        """シングルトンインスタンスを取得する。"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """シングルトンをリセットする（テスト用）。"""
        with cls._lock:
            cls._instance = None

    def create_user(self, request: UserCreateRequest) -> UserProfile:
        """ユーザーを作成する。

        Args:
            request: ユーザー作成リクエスト

        Returns:
            作成されたユーザープロファイル

        Raises:
            ValueError: 同じuser_idが既に存在する場合
        """
        with self._data_lock:
            if request.user_id in self._users:
                raise ValueError(
                    f"User with id '{request.user_id}' already exists"
                )

            now = datetime.now(timezone.utc)
            profile = UserProfile(
                user_id=request.user_id,
                plan=UserPlan.FREE,
                conversations=(),
                created_at=now,
                updated_at=now,
                preferred_categories=(),
            )

            # 不変パターン: 新しい辞書を作成
            self._users = {**self._users, request.user_id: profile}
            return profile

    def get_user(self, user_id: str) -> Optional[UserProfile]:
        """ユーザーを取得する。

        Args:
            user_id: ユーザーID

        Returns:
            ユーザープロファイル（見つからない場合はNone）
        """
        with self._data_lock:
            return self._users.get(user_id)

    def get_or_create_user(self, user_id: str) -> UserProfile:
        """ユーザーを取得、存在しない場合は作成する。

        Args:
            user_id: ユーザーID

        Returns:
            ユーザープロファイル
        """
        with self._data_lock:
            existing = self._users.get(user_id)
            if existing is not None:
                return existing
            now = datetime.now(timezone.utc)
            profile = UserProfile(user_id=user_id, created_at=now, updated_at=now)
            self._users = {**self._users, user_id: profile}
            return profile

    def update_user_plan(self, user_id: str, plan: UserPlan) -> UserProfile:
        """ユーザーのプランを更新する。

        Args:
            user_id: ユーザーID
            plan: 新しいプラン

        Returns:
            更新されたユーザープロファイル

        Raises:
            ValueError: ユーザーが見つからない場合
        """
        with self._data_lock:
            existing = self._users.get(user_id)
            if existing is None:
                raise ValueError(f"User '{user_id}' not found")

            # 不変パターン: 新しいUserProfileオブジェクトを作成
            updated = UserProfile(
                user_id=existing.user_id,
                plan=plan,
                conversations=existing.conversations,
                created_at=existing.created_at,
                updated_at=datetime.now(timezone.utc),
                preferred_categories=existing.preferred_categories,
            )

            self._users = {**self._users, user_id: updated}
            return updated

    def record_conversation(
        self,
        user_id: str,
        question: str,
        category: Optional[str] = None,
        feedback_score: Optional[int] = None,
    ) -> UserProfile:
        """会話履歴を記録する。

        Args:
            user_id: ユーザーID
            question: 質問内容
            category: カテゴリ（オプション）
            feedback_score: フィードバックスコア（オプション）

        Returns:
            更新されたユーザープロファイル

        Raises:
            ValueError: ユーザーが見つからない場合
        """
        with self._data_lock:
            existing = self._users.get(user_id)
            if existing is None:
                raise ValueError(f"User '{user_id}' not found")

            # 新しい会話レコードを作成
            new_record = ConversationRecord(
                question=question,
                category=category,
                feedback_score=feedback_score,
            )

            # 不変パターン: 新しいタプルを作成
            updated_conversations = existing.conversations + (new_record,)

            # カテゴリの統計を更新（頻度の高いカテゴリをpreferred_categoriesに）
            category_counts: dict[str, int] = {}
            for conv in updated_conversations:
                if conv.category:
                    category_counts[conv.category] = category_counts.get(conv.category, 0) + 1

            # 上位3カテゴリを抽出
            sorted_categories = sorted(
                category_counts.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:3]
            preferred_categories = tuple(cat for cat, _ in sorted_categories)

            updated = UserProfile(
                user_id=existing.user_id,
                plan=existing.plan,
                conversations=updated_conversations,
                created_at=existing.created_at,
                updated_at=datetime.now(timezone.utc),
                preferred_categories=preferred_categories,
            )

            self._users = {**self._users, user_id: updated}
            return updated

    def get_conversation_history(
        self,
        user_id: str,
        limit: int = 10,
        category: Optional[str] = None,
    ) -> list[ConversationRecord]:
        """会話履歴を取得する。

        Args:
            user_id: ユーザーID
            limit: 取得する最大件数
            category: フィルタするカテゴリ（オプション）

        Returns:
            会話履歴のリスト（新しい順）

        Raises:
            ValueError: ユーザーが見つからない場合
        """
        with self._data_lock:
            existing = self._users.get(user_id)
            if existing is None:
                raise ValueError(f"User '{user_id}' not found")

            conversations = list(existing.conversations)

        # カテゴリでフィルタ（ロック外）
        if category:
            conversations = [c for c in conversations if c.category == category]

        # 新しい順にソートして制限
        conversations.sort(key=lambda x: x.timestamp, reverse=True)
        return conversations[:limit]

    def update_preferred_categories(
        self,
        user_id: str,
        categories: list[str],
    ) -> UserProfile:
        """希望カテゴリを更新する。

        Args:
            user_id: ユーザーID
            categories: 希望カテゴリのリスト

        Returns:
            更新されたユーザープロファイル

        Raises:
            ValueError: ユーザーが見つからない場合
        """
        with self._data_lock:
            existing = self._users.get(user_id)
            if existing is None:
                raise ValueError(f"User '{user_id}' not found")

            updated = UserProfile(
                user_id=existing.user_id,
                plan=existing.plan,
                conversations=existing.conversations,
                created_at=existing.created_at,
                updated_at=datetime.now(timezone.utc),
                preferred_categories=tuple(categories),
            )

            self._users = {**self._users, user_id: updated}
            return updated

    def delete_user(self, user_id: str) -> None:
        """ユーザーを削除する。

        Args:
            user_id: ユーザーID

        Raises:
            ValueError: ユーザーが見つからない場合
        """
        with self._data_lock:
            if user_id not in self._users:
                raise ValueError(f"User '{user_id}' not found")

            # 不変パターン: 新しい辞書を作成（キーを除外）
            self._users = {k: v for k, v in self._users.items() if k != user_id}
