"""P3-55: A/Bテスト基盤 - Experiment モデルのテスト (TDD - GREEN phase)"""

import pytest
from datetime import datetime, timedelta
from enum import Enum
import pydantic


# ---------------------------------------------------------------------------
# ExperimentStatus Enum tests
# ---------------------------------------------------------------------------
class TestExperimentStatus:
    """実験ステータス列挙型のテスト"""

    def test_status_values(self):
        """ステータス値が正しく定義されている"""
        from app.models.experiment import ExperimentStatus
        assert ExperimentStatus.DRAFT.value == "draft"
        assert ExperimentStatus.RUNNING.value == "running"
        assert ExperimentStatus.COMPLETED.value == "completed"
        assert ExperimentStatus.STOPPED.value == "stopped"

    def test_status_count(self):
        """4つのステータスが定義されている"""
        from app.models.experiment import ExperimentStatus
        assert len(list(ExperimentStatus)) == 4


# ---------------------------------------------------------------------------
# MetricType Enum tests
# ---------------------------------------------------------------------------
class TestMetricType:
    """指標タイプ列挙型のテスト"""

    def test_metric_type_values(self):
        """指標タイプ値が正しく定義されている"""
        from app.models.experiment import MetricType
        assert MetricType.RESPONSE_QUALITY.value == "response_quality"
        assert MetricType.FEEDBACK_SCORE.value == "feedback_score"
        assert MetricType.RESOLUTION_RATE.value == "resolution_rate"

    def test_metric_type_count(self):
        """3つの指標タイプが定義されている"""
        from app.models.experiment import MetricType
        assert len(list(MetricType)) == 3


# ---------------------------------------------------------------------------
# Variant Model tests
# ---------------------------------------------------------------------------
class TestVariantModel:
    """バリアントモデルのテスト"""

    def test_variant_create_valid(self):
        """有効なバリアント作成"""
        from app.models.experiment import Variant
        variant = Variant(
            variant_id="control",
            name="Control Group",
            weight=0.5,
            config={"prompt": "default"},
        )
        assert variant.variant_id == "control"
        assert variant.name == "Control Group"
        assert variant.weight == 0.5
        assert variant.config == {"prompt": "default"}

    def test_variant_weight_validation_range(self):
        """重みは0〜1の範囲である必要がある"""
        from app.models.experiment import Variant
        with pytest.raises(pydantic.ValidationError):
            Variant(
                variant_id="invalid",
                name="Invalid Weight",
                weight=1.5,
                config={},
            )

    def test_variant_weight_validation_negative(self):
        """重みは負の値を許可しない"""
        from app.models.experiment import Variant
        with pytest.raises(pydantic.ValidationError):
            Variant(
                variant_id="negative",
                name="Negative Weight",
                weight=-0.1,
                config={},
            )

    def test_variant_immutability(self):
        """バリアントモデルは不変"""
        from app.models.experiment import Variant
        variant = Variant(
            variant_id="test",
            name="Test",
            weight=0.5,
            config={},
        )
        with pytest.raises((TypeError, pydantic.ValidationError)):
            variant.name = "Changed"

    def test_variant_config_defaults_to_empty_dict(self):
        """config のデフォルトは空の辞書"""
        from app.models.experiment import Variant
        variant = Variant(
            variant_id="default-config",
            name="Default Config",
            weight=0.5,
        )
        assert variant.config == {}


# ---------------------------------------------------------------------------
# Experiment Model tests
# ---------------------------------------------------------------------------
class TestExperimentModel:
    """実験モデルのテスト"""

    def test_experiment_create_valid(self):
        """有効な実験作成"""
        from app.models.experiment import Experiment, Variant, ExperimentStatus
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        experiment = Experiment(
            experiment_id="test-exp-001",
            name="Test Experiment",
            description="A test experiment",
            variants=variants,
            status=ExperimentStatus.DRAFT,
        )
        assert experiment.experiment_id == "test-exp-001"
        assert experiment.name == "Test Experiment"
        assert experiment.description == "A test experiment"
        assert len(experiment.variants) == 2
        assert experiment.status == ExperimentStatus.DRAFT

    def test_experiment_id_validation_empty(self):
        """実験名が空の場合はエラー"""
        from app.models.experiment import Experiment, Variant, ExperimentStatus
        with pytest.raises(pydantic.ValidationError):
            Experiment(
                experiment_id="",
                name="Empty ID",
                variants=[
                    Variant(variant_id="v1", name="V1", weight=1.0),
                ],
                status=ExperimentStatus.DRAFT,
            )

    def test_experiment_variants_validation_empty(self):
        """バリアントが空の場合はエラー"""
        from app.models.experiment import Experiment, ExperimentStatus
        with pytest.raises(pydantic.ValidationError):
            Experiment(
                experiment_id="no-variants",
                name="No Variants",
                variants=[],
                status=ExperimentStatus.DRAFT,
            )

    def test_experiment_variants_validation_single(self):
        """バリアントが1つだけの場合はエラー（A/Bテストには最低2つ必要）"""
        from app.models.experiment import Experiment, Variant, ExperimentStatus
        with pytest.raises(pydantic.ValidationError):
            Experiment(
                experiment_id="single-variant",
                name="Single Variant",
                variants=[
                    Variant(variant_id="only", name="Only", weight=1.0),
                ],
                status=ExperimentStatus.DRAFT,
            )

    def test_experiment_variant_weights_sum(self):
        """バリアントの重みの合計が1.0に近い必要がある（許容誤差 0.01）"""
        from app.models.experiment import Experiment, Variant, ExperimentStatus
        # 合計が0.9の場合はエラー
        with pytest.raises(pydantic.ValidationError):
            Experiment(
                experiment_id="invalid-weights",
                name="Invalid Weights",
                variants=[
                    Variant(variant_id="v1", name="V1", weight=0.5),
                    Variant(variant_id="v2", name="V2", weight=0.4),
                ],
                status=ExperimentStatus.DRAFT,
            )

    def test_experiment_variant_weights_valid(self):
        """バリアントの重みの合計が1.0の場合は有効"""
        from app.models.experiment import Experiment, Variant, ExperimentStatus
        experiment = Experiment(
            experiment_id="valid-weights",
            name="Valid Weights",
            variants=[
                Variant(variant_id="v1", name="V1", weight=0.5),
                Variant(variant_id="v2", name="V2", weight=0.5),
            ],
            status=ExperimentStatus.DRAFT,
        )
        assert experiment.experiment_id == "valid-weights"

    def test_experiment_immutability(self):
        """実験モデルは不変"""
        from app.models.experiment import Experiment, Variant, ExperimentStatus
        experiment = Experiment(
            experiment_id="immutable-test",
            name="Immutable Test",
            variants=[
                Variant(variant_id="v1", name="V1", weight=0.5),
                Variant(variant_id="v2", name="V2", weight=0.5),
            ],
            status=ExperimentStatus.DRAFT,
        )
        with pytest.raises((TypeError, pydantic.ValidationError)):
            experiment.name = "Changed"

    def test_experiment_status_default(self):
        """デフォルトステータスは DRAFT"""
        from app.models.experiment import Experiment, Variant, ExperimentStatus
        experiment = Experiment(
            experiment_id="default-status",
            name="Default Status",
            variants=[
                Variant(variant_id="v1", name="V1", weight=0.5),
                Variant(variant_id="v2", name="V2", weight=0.5),
            ],
        )
        assert experiment.status == ExperimentStatus.DRAFT

    def test_experiment_dates_optional(self):
        """開始日・終了日はオプション"""
        from app.models.experiment import Experiment, Variant, ExperimentStatus
        experiment = Experiment(
            experiment_id="optional-dates",
            name="Optional Dates",
            variants=[
                Variant(variant_id="v1", name="V1", weight=0.5),
                Variant(variant_id="v2", name="V2", weight=0.5),
            ],
        )
        assert experiment.start_date is None
        assert experiment.end_date is None


# ---------------------------------------------------------------------------
# ExperimentMetric Model tests
# ---------------------------------------------------------------------------
class TestExperimentMetricModel:
    """実験指標モデルのテスト"""

    def test_metric_create_valid(self):
        """有効な指標作成"""
        from app.models.experiment import ExperimentMetric, MetricType
        metric = ExperimentMetric(
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

    def test_metric_immutability(self):
        """指標モデルは不変"""
        from app.models.experiment import ExperimentMetric, MetricType
        metric = ExperimentMetric(
            experiment_id="exp-001",
            variant_id="control",
            user_id="user-123",
            metric_type=MetricType.FEEDBACK_SCORE,
            value=1,
        )
        with pytest.raises((TypeError, pydantic.ValidationError)):
            metric.value = 0

    def test_metric_has_timestamp(self):
        """指標にはタイムスタンプがある"""
        from app.models.experiment import ExperimentMetric, MetricType
        fixed_timestamp = datetime(2026, 2, 27, 12, 0, 0)
        metric = ExperimentMetric(
            experiment_id="exp-001",
            variant_id="control",
            user_id="user-123",
            metric_type=MetricType.RESOLUTION_RATE,
            value=1,
            timestamp=fixed_timestamp,
        )
        assert metric.timestamp == fixed_timestamp

    def test_metric_timestamp_auto_generated(self):
        """タイムスタンプが自動生成される"""
        from app.models.experiment import ExperimentMetric, MetricType
        before = datetime.now()
        metric = ExperimentMetric(
            experiment_id="exp-001",
            variant_id="control",
            user_id="user-123",
            metric_type=MetricType.RESOLUTION_RATE,
            value=1,
        )
        after = datetime.now()
        # タイムスタンプが設定されていることを確認
        assert metric.timestamp is not None
        assert isinstance(metric.timestamp, datetime)
        # 妥当な範囲内にあることを確認
        assert metric.timestamp >= before - timedelta(seconds=1)
        assert metric.timestamp <= after + timedelta(seconds=1)


# ---------------------------------------------------------------------------
# Request/Response Model tests
# ---------------------------------------------------------------------------
class TestExperimentRequestModels:
    """リクエスト/レスポンスモデルのテスト"""

    def test_experiment_create_request(self):
        """実験作成リクエスト"""
        from app.models.experiment import (
            ExperimentCreateRequest,
            VariantCreateRequest,
        )
        request = ExperimentCreateRequest(
            experiment_id="new-exp",
            name="New Experiment",
            description="Description",
            variants=[
                VariantCreateRequest(
                    variant_id="control",
                    name="Control",
                    weight=0.5,
                ),
                VariantCreateRequest(
                    variant_id="treatment",
                    name="Treatment",
                    weight=0.5,
                ),
            ],
        )
        assert request.experiment_id == "new-exp"
        assert len(request.variants) == 2

    def test_variant_assign_request(self):
        """バリアント割り当てリクエスト（experiment_idはパスパラメータ）"""
        from app.models.experiment import VariantAssignRequest
        request = VariantAssignRequest(
            user_id="user-123",
        )
        assert request.user_id == "user-123"

    def test_metric_record_request(self):
        """指標記録リクエスト（experiment_idはパスパラメータ）"""
        from app.models.experiment import MetricRecordRequest, MetricType
        request = MetricRecordRequest(
            variant_id="control",
            user_id="user-123",
            metric_type=MetricType.RESPONSE_QUALITY,
            value=4.0,
        )
        assert request.variant_id == "control"
        assert request.metric_type == MetricType.RESPONSE_QUALITY
        assert request.value == 4.0
