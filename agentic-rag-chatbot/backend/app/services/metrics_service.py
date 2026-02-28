"""P3-55: A/Bテスト基盤 - 指標収集サービス"""

import statistics
from datetime import datetime
from threading import Lock
from typing import Optional

from app.models.experiment import ExperimentMetric, MetricType


class MetricsService:
    """指標収集・集計サービス（シングルトン）"""

    _instance: Optional["MetricsService"] = None
    _lock: Lock = Lock()

    def __init__(self) -> None:
        """サービスの初期化"""
        self._metrics: list[ExperimentMetric] = []

    @classmethod
    def get_instance(cls) -> "MetricsService":
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

    def record_metric(
        self,
        experiment_id: str,
        variant_id: str,
        user_id: str,
        metric_type: MetricType,
        value: float,
        timestamp: Optional[datetime] = None,
    ) -> ExperimentMetric:
        """指標を記録する。

        Args:
            experiment_id: 実験ID
            variant_id: バリアントID
            user_id: ユーザーID
            metric_type: 指標タイプ
            value: 指標値
            timestamp: タイムスタンプ（省略時は現在時刻）

        Returns:
            記録された指標
        """
        metric = ExperimentMetric(
            experiment_id=experiment_id,
            variant_id=variant_id,
            user_id=user_id,
            metric_type=metric_type,
            value=value,
            timestamp=timestamp or datetime.now(),
        )

        # 不変パターン: 新しいリストを作成
        self._metrics = [*self._metrics, metric]
        return metric

    def get_metrics(
        self,
        experiment_id: str,
        variant_id: Optional[str] = None,
        metric_type: Optional[MetricType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[ExperimentMetric]:
        """指標を取得する。

        Args:
            experiment_id: 実験ID
            variant_id: バリアントID（省略時は全バリアント）
            metric_type: 指標タイプ（省略時は全タイプ）
            start_date: 開始日（省略時は制限なし）
            end_date: 終了日（省略時は制限なし）

        Returns:
            フィルタリングされた指標のリスト
        """
        metrics = [
            m for m in self._metrics if m.experiment_id == experiment_id
        ]

        if variant_id is not None:
            metrics = [m for m in metrics if m.variant_id == variant_id]

        if metric_type is not None:
            metrics = [m for m in metrics if m.metric_type == metric_type]

        if start_date is not None:
            metrics = [m for m in metrics if m.timestamp >= start_date]

        if end_date is not None:
            metrics = [m for m in metrics if m.timestamp <= end_date]

        return metrics

    def aggregate_metrics(
        self,
        experiment_id: str,
        variant_id: str,
        metric_type: MetricType,
        aggregation: str = "mean",
    ) -> Optional[float]:
        """指標を集計する。

        Args:
            experiment_id: 実験ID
            variant_id: バリアントID
            metric_type: 指標タイプ
            aggregation: 集計方法（"mean", "sum", "count"）

        Returns:
            集計値（指標がない場合はNone）
        """
        metrics = self.get_metrics(
            experiment_id=experiment_id,
            variant_id=variant_id,
            metric_type=metric_type,
        )

        if not metrics:
            return None

        values = [m.value for m in metrics]

        if aggregation == "mean":
            return statistics.mean(values)
        elif aggregation == "sum":
            return sum(values)
        elif aggregation == "count":
            return float(len(values))
        else:
            raise ValueError(f"Unknown aggregation method: {aggregation}")

    def get_variant_statistics(
        self,
        experiment_id: str,
        metric_type: MetricType,
    ) -> dict[str, dict[str, float]]:
        """バリアントごとの統計を取得する。

        Args:
            experiment_id: 実験ID
            metric_type: 指標タイプ

        Returns:
            バリアントIDをキーとする統計辞書
            各バリアントの統計には mean, std, count, sum が含まれる
        """
        metrics = self.get_metrics(
            experiment_id=experiment_id,
            metric_type=metric_type,
        )

        # バリアントごとにグループ化
        variant_values: dict[str, list[float]] = {}
        for m in metrics:
            if m.variant_id not in variant_values:
                variant_values[m.variant_id] = []
            variant_values[m.variant_id].append(m.value)

        result: dict[str, dict[str, float]] = {}
        for variant_id, values in variant_values.items():
            if values:
                result[variant_id] = {
                    "mean": statistics.mean(values),
                    "sum": sum(values),
                    "count": float(len(values)),
                }
                # 標準偏差は2件以上の場合のみ計算
                if len(values) >= 2:
                    result[variant_id]["std"] = statistics.stdev(values)
                else:
                    result[variant_id]["std"] = 0.0

        return result
