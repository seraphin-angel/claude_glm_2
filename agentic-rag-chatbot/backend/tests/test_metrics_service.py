"""P3-55: A/Bテスト基盤 - MetricsService のテスト (TDD - RED phase)"""

import pytest
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Metric Recording tests
# ---------------------------------------------------------------------------
class TestMetricRecording:
    """指標記録のテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.metrics_service import MetricsService
        MetricsService.reset_instance()
        yield
        MetricsService.reset_instance()

    def test_record_metric(self):
        """指標を記録できる"""
        from app.services.metrics_service import MetricsService
        from app.models.experiment import MetricType

        service = MetricsService.get_instance()
        metric = service.record_metric(
            experiment_id="exp-001",
            variant_id="control",
            user_id="user-123",
            metric_type=MetricType.RESPONSE_QUALITY,
            value=4.5,
        )

        assert metric.experiment_id == "exp-001"
        assert metric.variant_id == "control"
        assert metric.user_id == "user-123"
        assert metric.metric_type == MetricType.RESPONSE_QUALITY
        assert metric.value == 4.5

    def test_record_multiple_metrics(self):
        """複数の指標を記録できる"""
        from app.services.metrics_service import MetricsService
        from app.models.experiment import MetricType

        service = MetricsService.get_instance()
        for i in range(10):
            service.record_metric(
                experiment_id="exp-001",
                variant_id="control" if i % 2 == 0 else "treatment",
                user_id=f"user-{i}",
                metric_type=MetricType.FEEDBACK_SCORE,
                value=1 if i % 2 == 0 else -1,
            )

        metrics = service.get_metrics("exp-001")
        assert len(metrics) == 10

    def test_get_metrics_by_variant(self):
        """バリアントごとに指標を取得できる"""
        from app.services.metrics_service import MetricsService
        from app.models.experiment import MetricType

        service = MetricsService.get_instance()
        # Control: 5件
        for i in range(5):
            service.record_metric(
                experiment_id="exp-001",
                variant_id="control",
                user_id=f"control-user-{i}",
                metric_type=MetricType.RESPONSE_QUALITY,
                value=4.0,
            )
        # Treatment: 3件
        for i in range(3):
            service.record_metric(
                experiment_id="exp-001",
                variant_id="treatment",
                user_id=f"treatment-user-{i}",
                metric_type=MetricType.RESPONSE_QUALITY,
                value=4.5,
            )

        control_metrics = service.get_metrics("exp-001", variant_id="control")
        treatment_metrics = service.get_metrics("exp-001", variant_id="treatment")

        assert len(control_metrics) == 5
        assert len(treatment_metrics) == 3

    def test_get_metrics_by_type(self):
        """指標タイプでフィルタリングできる"""
        from app.services.metrics_service import MetricsService
        from app.models.experiment import MetricType

        service = MetricsService.get_instance()
        service.record_metric(
            experiment_id="exp-001",
            variant_id="control",
            user_id="user-1",
            metric_type=MetricType.RESPONSE_QUALITY,
            value=4.0,
        )
        service.record_metric(
            experiment_id="exp-001",
            variant_id="control",
            user_id="user-2",
            metric_type=MetricType.FEEDBACK_SCORE,
            value=1,
        )

        quality_metrics = service.get_metrics(
            "exp-001", metric_type=MetricType.RESPONSE_QUALITY
        )
        feedback_metrics = service.get_metrics(
            "exp-001", metric_type=MetricType.FEEDBACK_SCORE
        )

        assert len(quality_metrics) == 1
        assert len(feedback_metrics) == 1


# ---------------------------------------------------------------------------
# Metric Aggregation tests
# ---------------------------------------------------------------------------
class TestMetricAggregation:
    """指標集計のテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.metrics_service import MetricsService
        MetricsService.reset_instance()
        yield
        MetricsService.reset_instance()

    def test_aggregate_average(self):
        """平均値を集計できる"""
        from app.services.metrics_service import MetricsService
        from app.models.experiment import MetricType

        service = MetricsService.get_instance()
        values = [3.0, 4.0, 5.0]
        for i, v in enumerate(values):
            service.record_metric(
                experiment_id="exp-001",
                variant_id="control",
                user_id=f"user-{i}",
                metric_type=MetricType.RESPONSE_QUALITY,
                value=v,
            )

        result = service.aggregate_metrics(
            experiment_id="exp-001",
            variant_id="control",
            metric_type=MetricType.RESPONSE_QUALITY,
            aggregation="mean",
        )

        assert result == pytest.approx(4.0)

    def test_aggregate_sum(self):
        """合計値を集計できる"""
        from app.services.metrics_service import MetricsService
        from app.models.experiment import MetricType

        service = MetricsService.get_instance()
        values = [1, 1, -1, 1]
        for i, v in enumerate(values):
            service.record_metric(
                experiment_id="exp-001",
                variant_id="control",
                user_id=f"user-{i}",
                metric_type=MetricType.FEEDBACK_SCORE,
                value=v,
            )

        result = service.aggregate_metrics(
            experiment_id="exp-001",
            variant_id="control",
            metric_type=MetricType.FEEDBACK_SCORE,
            aggregation="sum",
        )

        assert result == 2

    def test_aggregate_count(self):
        """カウントを集計できる"""
        from app.services.metrics_service import MetricsService
        from app.models.experiment import MetricType

        service = MetricsService.get_instance()
        for i in range(10):
            service.record_metric(
                experiment_id="exp-001",
                variant_id="control",
                user_id=f"user-{i}",
                metric_type=MetricType.RESOLUTION_RATE,
                value=1 if i < 7 else 0,
            )

        result = service.aggregate_metrics(
            experiment_id="exp-001",
            variant_id="control",
            metric_type=MetricType.RESOLUTION_RATE,
            aggregation="count",
        )

        assert result == 10

    def test_aggregate_empty_returns_none(self):
        """指標がない場合は None を返す"""
        from app.services.metrics_service import MetricsService
        from app.models.experiment import MetricType

        service = MetricsService.get_instance()
        result = service.aggregate_metrics(
            experiment_id="exp-001",
            variant_id="control",
            metric_type=MetricType.RESPONSE_QUALITY,
            aggregation="mean",
        )

        assert result is None


# ---------------------------------------------------------------------------
# Date Filtering tests
# ---------------------------------------------------------------------------
class TestDateFiltering:
    """日付フィルタリングのテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.metrics_service import MetricsService
        MetricsService.reset_instance()
        yield
        MetricsService.reset_instance()

    def test_filter_by_date_range(self):
        """日付範囲でフィルタリングできる"""
        from app.services.metrics_service import MetricsService
        from app.models.experiment import MetricType

        service = MetricsService.get_instance()
        now = datetime.now()

        # 過去の指標（10日前）
        past_date = now - timedelta(days=10)
        service.record_metric(
            experiment_id="exp-001",
            variant_id="control",
            user_id="old-user",
            metric_type=MetricType.RESPONSE_QUALITY,
            value=3.0,
            timestamp=past_date,
        )

        # 最近の指標（1日前）
        recent_date = now - timedelta(days=1)
        service.record_metric(
            experiment_id="exp-001",
            variant_id="control",
            user_id="recent-user",
            metric_type=MetricType.RESPONSE_QUALITY,
            value=5.0,
            timestamp=recent_date,
        )

        # 過去7日間のみ取得
        start_date = now - timedelta(days=7)
        metrics = service.get_metrics(
            "exp-001",
            start_date=start_date,
        )

        assert len(metrics) == 1
        assert metrics[0].user_id == "recent-user"

    def test_filter_by_end_date(self):
        """終了日でフィルタリングできる"""
        from app.services.metrics_service import MetricsService
        from app.models.experiment import MetricType

        service = MetricsService.get_instance()
        now = datetime.now()

        # 過去の指標
        past_date = now - timedelta(days=10)
        service.record_metric(
            experiment_id="exp-001",
            variant_id="control",
            user_id="old-user",
            metric_type=MetricType.RESPONSE_QUALITY,
            value=3.0,
            timestamp=past_date,
        )

        # 最近の指標
        recent_date = now - timedelta(days=1)
        service.record_metric(
            experiment_id="exp-001",
            variant_id="control",
            user_id="recent-user",
            metric_type=MetricType.RESPONSE_QUALITY,
            value=5.0,
            timestamp=recent_date,
        )

        # 5日前までのデータのみ取得
        end_date = now - timedelta(days=5)
        metrics = service.get_metrics(
            "exp-001",
            end_date=end_date,
        )

        assert len(metrics) == 1
        assert metrics[0].user_id == "old-user"


# ---------------------------------------------------------------------------
# Variant Statistics tests
# ---------------------------------------------------------------------------
class TestVariantStatistics:
    """バリアント統計のテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.metrics_service import MetricsService
        MetricsService.reset_instance()
        yield
        MetricsService.reset_instance()

    def test_get_variant_statistics(self):
        """バリアントごとの統計を取得できる"""
        from app.services.metrics_service import MetricsService
        from app.models.experiment import MetricType

        service = MetricsService.get_instance()

        # Control: 平均 4.0
        for i, v in enumerate([3.0, 4.0, 5.0]):
            service.record_metric(
                experiment_id="exp-001",
                variant_id="control",
                user_id=f"control-user-{i}",
                metric_type=MetricType.RESPONSE_QUALITY,
                value=v,
            )

        # Treatment: 平均 3.0
        for i, v in enumerate([2.0, 3.0, 4.0]):
            service.record_metric(
                experiment_id="exp-001",
                variant_id="treatment",
                user_id=f"treatment-user-{i}",
                metric_type=MetricType.RESPONSE_QUALITY,
                value=v,
            )

        stats = service.get_variant_statistics(
            experiment_id="exp-001",
            metric_type=MetricType.RESPONSE_QUALITY,
        )

        assert "control" in stats
        assert "treatment" in stats
        assert stats["control"]["mean"] == pytest.approx(4.0)
        assert stats["treatment"]["mean"] == pytest.approx(3.0)
        assert stats["control"]["count"] == 3
        assert stats["treatment"]["count"] == 3

    def test_variant_statistics_include_std(self):
        """統計に標準偏差が含まれる"""
        from app.services.metrics_service import MetricsService
        from app.models.experiment import MetricType

        service = MetricsService.get_instance()
        values = [2.0, 4.0, 6.0]
        for i, v in enumerate(values):
            service.record_metric(
                experiment_id="exp-001",
                variant_id="control",
                user_id=f"user-{i}",
                metric_type=MetricType.RESPONSE_QUALITY,
                value=v,
            )

        stats = service.get_variant_statistics(
            experiment_id="exp-001",
            metric_type=MetricType.RESPONSE_QUALITY,
        )

        # 標準偏差: sqrt(((2-4)^2 + (4-4)^2 + (6-4)^2) / 3) = sqrt(8/3) ≈ 1.63
        assert stats["control"]["std"] == pytest.approx(2.0, rel=0.01)
