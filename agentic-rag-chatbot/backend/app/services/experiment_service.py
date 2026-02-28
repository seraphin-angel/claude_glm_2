"""P3-55: A/Bテスト基盤 - 実験サービス（バリアント割り当て、CRUD管理）"""

import hashlib
from datetime import datetime
from threading import Lock
from typing import Optional

from app.models.experiment import (
    Experiment,
    ExperimentCreateRequest,
    ExperimentStatus,
    Variant,
)


class ExperimentService:
    """実験管理サービス（シングルトン）"""

    _instance: Optional["ExperimentService"] = None
    _lock: Lock = Lock()

    def __init__(self) -> None:
        """サービスの初期化"""
        self._experiments: dict[str, Experiment] = {}

    @classmethod
    def get_instance(cls) -> "ExperimentService":
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

    def create_experiment(self, request: ExperimentCreateRequest) -> Experiment:
        """実験を作成する。

        Args:
            request: 実験作成リクエスト

        Returns:
            作成された実験

        Raises:
            ValueError: 同じexperiment_idが既に存在する場合
        """
        if request.experiment_id in self._experiments:
            raise ValueError(
                f"Experiment with id '{request.experiment_id}' already exists"
            )

        variants = [
            Variant(
                variant_id=v.variant_id,
                name=v.name,
                weight=v.weight,
                config=v.config,
            )
            for v in request.variants
        ]

        experiment = Experiment(
            experiment_id=request.experiment_id,
            name=request.name,
            description=request.description,
            variants=variants,
            status=ExperimentStatus.DRAFT,
            metrics=request.metrics,
        )

        # 不変パターン: 新しい辞書を作成
        self._experiments = {**self._experiments, request.experiment_id: experiment}
        return experiment

    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """実験を取得する。

        Args:
            experiment_id: 実験ID

        Returns:
            実験（見つからない場合はNone）
        """
        return self._experiments.get(experiment_id)

    def list_experiments(
        self,
        status: Optional[ExperimentStatus] = None,
    ) -> list[Experiment]:
        """実験一覧を取得する。

        Args:
            status: フィルタリングするステータス（Noneの場合は全て）

        Returns:
            実験のリスト
        """
        experiments = list(self._experiments.values())
        if status is not None:
            experiments = [e for e in experiments if e.status == status]
        return experiments

    def update_status(
        self,
        experiment_id: str,
        new_status: ExperimentStatus,
    ) -> Experiment:
        """実験のステータスを更新する。

        Args:
            experiment_id: 実験ID
            new_status: 新しいステータス

        Returns:
            更新された実験

        Raises:
            ValueError: 実験が見つからない場合、または無効なステータス遷移の場合
        """
        existing = self._experiments.get(experiment_id)
        if existing is None:
            raise ValueError(f"Experiment '{experiment_id}' not found")

        # 完了/停止済みの実験は再開できない
        if existing.status in (ExperimentStatus.COMPLETED, ExperimentStatus.STOPPED):
            if new_status == ExperimentStatus.RUNNING:
                raise ValueError(
                    f"Experiment '{experiment_id}' cannot be restarted "
                    f"(current status: {existing.status.value})"
                )

        # 不変パターン: 新しいExperimentオブジェクトを作成
        now = datetime.now()
        start_date = existing.start_date
        end_date = existing.end_date

        if new_status == ExperimentStatus.RUNNING and existing.status != ExperimentStatus.RUNNING:
            start_date = now
        elif new_status in (ExperimentStatus.COMPLETED, ExperimentStatus.STOPPED):
            end_date = now

        updated = Experiment(
            experiment_id=existing.experiment_id,
            name=existing.name,
            description=existing.description,
            variants=existing.variants,
            status=new_status,
            start_date=start_date,
            end_date=end_date,
            metrics=existing.metrics,
        )

        self._experiments = {**self._experiments, experiment_id: updated}
        return updated

    def assign_variant(self, experiment_id: str, user_id: str) -> str:
        """ユーザーにバリアントを割り当てる。

        ハッシュベースの決定的な割り当てを行う。
        同じユーザーは常に同じバリアントに割り当てられる。

        Args:
            experiment_id: 実験ID
            user_id: ユーザーID

        Returns:
            割り当てられたバリアントID

        Raises:
            ValueError: 実験が見つからない場合、または実験が実行中でない場合
        """
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            raise ValueError(f"Experiment '{experiment_id}' not found")

        if experiment.status != ExperimentStatus.RUNNING:
            raise ValueError(
                f"Experiment '{experiment_id}' is not running "
                f"(current status: {experiment.status.value})"
            )

        # ユーザーID + 実験ID のハッシュで決定的な値を生成
        hash_input = f"{experiment_id}:{user_id}"
        hash_value = int(hashlib.sha256(hash_input.encode()).hexdigest(), 16)
        # 0.0 〜 1.0 の範囲に正規化
        normalized = (hash_value % 10000) / 10000.0

        # 重み付けに基づいてバリアントを選択
        cumulative_weight = 0.0
        for variant in experiment.variants:
            cumulative_weight += variant.weight
            if normalized < cumulative_weight:
                return variant.variant_id

        # 浮動小数点の誤差対策: 最後のバリアントを返す
        return experiment.variants[-1].variant_id
