"""P3-55: A/Bテスト基盤 - ExperimentService のテスト (TDD - RED phase)"""

import pytest
from datetime import datetime
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Variant Assignment tests
# ---------------------------------------------------------------------------
class TestVariantAssignment:
    """バリアント割り当てのテスト"""

    def test_assign_variant_deterministic(self):
        """同一ユーザーは常に同じバリアントに割り当てられる（決定性）"""
        from app.services.experiment_service import ExperimentService
        from app.models.experiment import Variant, Experiment, ExperimentStatus

        service = ExperimentService.get_instance()
        service.reset_instance()
        service = ExperimentService.get_instance()

        # テスト用の実験を作成
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        experiment = Experiment(
            experiment_id="deterministic-test",
            name="Deterministic Test",
            variants=variants,
            status=ExperimentStatus.RUNNING,
        )
        service._experiments = {"deterministic-test": experiment}

        # 同じユーザーに複数回割り当て
        result1 = service.assign_variant("deterministic-test", "user-123")
        result2 = service.assign_variant("deterministic-test", "user-123")
        result3 = service.assign_variant("deterministic-test", "user-123")

        assert result1 == result2 == result3
        assert result1 in ["control", "treatment"]

    def test_assign_variant_different_users(self):
        """異なるユーザーは異なるバリアントに割り当てられる可能性がある"""
        from app.services.experiment_service import ExperimentService
        from app.models.experiment import Variant, Experiment, ExperimentStatus

        service = ExperimentService.get_instance()
        service.reset_instance()
        service = ExperimentService.get_instance()

        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        experiment = Experiment(
            experiment_id="diff-users-test",
            name="Diff Users Test",
            variants=variants,
            status=ExperimentStatus.RUNNING,
        )
        service._experiments = {"diff-users-test": experiment}

        # 多くのユーザーで割り当てを行い、両方のバリアントに割り当てられることを確認
        assigned_variants = set()
        for i in range(100):
            variant = service.assign_variant("diff-users-test", f"user-{i}")
            assigned_variants.add(variant)

        # 100人のユーザーで両方のバリアントに割り当てられるはず
        assert len(assigned_variants) == 2

    def test_assign_variant_weighted_distribution(self):
        """重み付けに基づいてバリアントが分配される（70/30分割）"""
        from app.services.experiment_service import ExperimentService
        from app.models.experiment import Variant, Experiment, ExperimentStatus

        service = ExperimentService.get_instance()
        service.reset_instance()
        service = ExperimentService.get_instance()

        variants = [
            Variant(variant_id="control", name="Control", weight=0.7),
            Variant(variant_id="treatment", name="Treatment", weight=0.3),
        ]
        experiment = Experiment(
            experiment_id="weighted-test",
            name="Weighted Test",
            variants=variants,
            status=ExperimentStatus.RUNNING,
        )
        service._experiments = {"weighted-test": experiment}

        # 多数のユーザーで割り当てを行い、分布を確認
        assignments = {"control": 0, "treatment": 0}
        for i in range(1000):
            variant = service.assign_variant("weighted-test", f"user-{i}")
            assignments[variant] += 1

        # 70/30 の分布に近いことを確認（許容誤差 5%）
        control_ratio = assignments["control"] / 1000
        assert 0.65 <= control_ratio <= 0.75, f"Control ratio: {control_ratio}"

    def test_assign_variant_nonexistent_experiment(self):
        """存在しない実験に割り当てようとするとエラー"""
        from app.services.experiment_service import ExperimentService

        service = ExperimentService.get_instance()
        service.reset_instance()
        service = ExperimentService.get_instance()

        with pytest.raises(ValueError, match="not found"):
            service.assign_variant("nonexistent", "user-123")

    def test_assign_variant_draft_experiment(self):
        """DRAFT状態の実験には割り当てできない"""
        from app.services.experiment_service import ExperimentService
        from app.models.experiment import Variant, Experiment, ExperimentStatus

        service = ExperimentService.get_instance()
        service.reset_instance()
        service = ExperimentService.get_instance()

        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        experiment = Experiment(
            experiment_id="draft-exp",
            name="Draft Experiment",
            variants=variants,
            status=ExperimentStatus.DRAFT,
        )
        service._experiments = {"draft-exp": experiment}

        with pytest.raises(ValueError, match="not running"):
            service.assign_variant("draft-exp", "user-123")


# ---------------------------------------------------------------------------
# Experiment CRUD tests
# ---------------------------------------------------------------------------
class TestExperimentCRUD:
    """実験のCRUD操作のテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.experiment_service import ExperimentService
        ExperimentService.reset_instance()
        yield
        ExperimentService.reset_instance()

    def test_create_experiment(self):
        """実験を作成できる"""
        from app.services.experiment_service import ExperimentService
        from app.models.experiment import (
            ExperimentCreateRequest,
            VariantCreateRequest,
        )

        service = ExperimentService.get_instance()
        request = ExperimentCreateRequest(
            experiment_id="new-exp",
            name="New Experiment",
            description="Test description",
            variants=[
                VariantCreateRequest(variant_id="control", name="Control", weight=0.5),
                VariantCreateRequest(variant_id="treatment", name="Treatment", weight=0.5),
            ],
        )
        experiment = service.create_experiment(request)

        assert experiment.experiment_id == "new-exp"
        assert experiment.name == "New Experiment"
        assert len(experiment.variants) == 2

    def test_create_duplicate_experiment(self):
        """重複する実験IDは作成不可"""
        from app.services.experiment_service import ExperimentService
        from app.models.experiment import (
            ExperimentCreateRequest,
            VariantCreateRequest,
        )

        service = ExperimentService.get_instance()
        request = ExperimentCreateRequest(
            experiment_id="dup-exp",
            name="Duplicate",
            variants=[
                VariantCreateRequest(variant_id="control", name="Control", weight=0.5),
                VariantCreateRequest(variant_id="treatment", name="Treatment", weight=0.5),
            ],
        )
        service.create_experiment(request)

        with pytest.raises(ValueError, match="already exists"):
            service.create_experiment(request)

    def test_get_experiment(self):
        """実験を取得できる"""
        from app.services.experiment_service import ExperimentService
        from app.models.experiment import (
            ExperimentCreateRequest,
            VariantCreateRequest,
        )

        service = ExperimentService.get_instance()
        request = ExperimentCreateRequest(
            experiment_id="get-test",
            name="Get Test",
            variants=[
                VariantCreateRequest(variant_id="control", name="Control", weight=0.5),
                VariantCreateRequest(variant_id="treatment", name="Treatment", weight=0.5),
            ],
        )
        service.create_experiment(request)

        experiment = service.get_experiment("get-test")
        assert experiment is not None
        assert experiment.experiment_id == "get-test"

    def test_get_nonexistent_experiment(self):
        """存在しない実験はNoneを返す"""
        from app.services.experiment_service import ExperimentService

        service = ExperimentService.get_instance()
        experiment = service.get_experiment("nonexistent")
        assert experiment is None

    def test_list_experiments(self):
        """実験一覧を取得できる"""
        from app.services.experiment_service import ExperimentService
        from app.models.experiment import (
            ExperimentCreateRequest,
            VariantCreateRequest,
        )

        service = ExperimentService.get_instance()
        for i in range(3):
            request = ExperimentCreateRequest(
                experiment_id=f"list-exp-{i}",
                name=f"List Experiment {i}",
                variants=[
                    VariantCreateRequest(variant_id="control", name="Control", weight=0.5),
                    VariantCreateRequest(variant_id="treatment", name="Treatment", weight=0.5),
                ],
            )
            service.create_experiment(request)

        experiments = service.list_experiments()
        assert len(experiments) == 3

    def test_list_experiments_filter_by_status(self):
        """ステータスでフィルタリングできる"""
        from app.services.experiment_service import ExperimentService
        from app.models.experiment import (
            ExperimentCreateRequest,
            VariantCreateRequest,
            ExperimentStatus,
        )

        service = ExperimentService.get_instance()
        # DRAFT実験
        request = ExperimentCreateRequest(
            experiment_id="draft-filter",
            name="Draft",
            variants=[
                VariantCreateRequest(variant_id="control", name="Control", weight=0.5),
                VariantCreateRequest(variant_id="treatment", name="Treatment", weight=0.5),
            ],
        )
        service.create_experiment(request)

        # RUNNING実験
        request = ExperimentCreateRequest(
            experiment_id="running-filter",
            name="Running",
            variants=[
                VariantCreateRequest(variant_id="control", name="Control", weight=0.5),
                VariantCreateRequest(variant_id="treatment", name="Treatment", weight=0.5),
            ],
        )
        service.create_experiment(request)
        service.update_status("running-filter", ExperimentStatus.RUNNING)

        running_experiments = service.list_experiments(status=ExperimentStatus.RUNNING)
        assert len(running_experiments) == 1
        assert running_experiments[0].experiment_id == "running-filter"


# ---------------------------------------------------------------------------
# Status Management tests
# ---------------------------------------------------------------------------
class TestStatusManagement:
    """ステータス管理のテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.experiment_service import ExperimentService
        ExperimentService.reset_instance()
        yield
        ExperimentService.reset_instance()

    def test_start_experiment(self):
        """実験を開始できる"""
        from app.services.experiment_service import ExperimentService
        from app.models.experiment import (
            ExperimentCreateRequest,
            VariantCreateRequest,
            ExperimentStatus,
        )

        service = ExperimentService.get_instance()
        request = ExperimentCreateRequest(
            experiment_id="start-test",
            name="Start Test",
            variants=[
                VariantCreateRequest(variant_id="control", name="Control", weight=0.5),
                VariantCreateRequest(variant_id="treatment", name="Treatment", weight=0.5),
            ],
        )
        service.create_experiment(request)

        updated = service.update_status("start-test", ExperimentStatus.RUNNING)
        assert updated.status == ExperimentStatus.RUNNING
        assert updated.start_date is not None

    def test_stop_experiment(self):
        """実験を停止できる"""
        from app.services.experiment_service import ExperimentService
        from app.models.experiment import (
            ExperimentCreateRequest,
            VariantCreateRequest,
            ExperimentStatus,
        )

        service = ExperimentService.get_instance()
        request = ExperimentCreateRequest(
            experiment_id="stop-test",
            name="Stop Test",
            variants=[
                VariantCreateRequest(variant_id="control", name="Control", weight=0.5),
                VariantCreateRequest(variant_id="treatment", name="Treatment", weight=0.5),
            ],
        )
        service.create_experiment(request)
        service.update_status("stop-test", ExperimentStatus.RUNNING)

        updated = service.update_status("stop-test", ExperimentStatus.STOPPED)
        assert updated.status == ExperimentStatus.STOPPED
        assert updated.end_date is not None

    def test_complete_experiment(self):
        """実験を完了できる"""
        from app.services.experiment_service import ExperimentService
        from app.models.experiment import (
            ExperimentCreateRequest,
            VariantCreateRequest,
            ExperimentStatus,
        )

        service = ExperimentService.get_instance()
        request = ExperimentCreateRequest(
            experiment_id="complete-test",
            name="Complete Test",
            variants=[
                VariantCreateRequest(variant_id="control", name="Control", weight=0.5),
                VariantCreateRequest(variant_id="treatment", name="Treatment", weight=0.5),
            ],
        )
        service.create_experiment(request)
        service.update_status("complete-test", ExperimentStatus.RUNNING)

        updated = service.update_status("complete-test", ExperimentStatus.COMPLETED)
        assert updated.status == ExperimentStatus.COMPLETED
        assert updated.end_date is not None

    def test_update_status_nonexistent_experiment(self):
        """存在しない実験のステータス更新はエラー"""
        from app.services.experiment_service import ExperimentService
        from app.models.experiment import ExperimentStatus

        service = ExperimentService.get_instance()
        with pytest.raises(ValueError, match="not found"):
            service.update_status("nonexistent", ExperimentStatus.RUNNING)

    def test_cannot_restart_completed_experiment(self):
        """完了した実験は再開できない"""
        from app.services.experiment_service import ExperimentService
        from app.models.experiment import (
            ExperimentCreateRequest,
            VariantCreateRequest,
            ExperimentStatus,
        )

        service = ExperimentService.get_instance()
        request = ExperimentCreateRequest(
            experiment_id="no-restart",
            name="No Restart",
            variants=[
                VariantCreateRequest(variant_id="control", name="Control", weight=0.5),
                VariantCreateRequest(variant_id="treatment", name="Treatment", weight=0.5),
            ],
        )
        service.create_experiment(request)
        service.update_status("no-restart", ExperimentStatus.RUNNING)
        service.update_status("no-restart", ExperimentStatus.COMPLETED)

        with pytest.raises(ValueError, match="cannot be restarted"):
            service.update_status("no-restart", ExperimentStatus.RUNNING)


# ---------------------------------------------------------------------------
# Singleton Pattern tests
# ---------------------------------------------------------------------------
class TestSingletonPattern:
    """シングルトンパターンのテスト"""

    def test_singleton_returns_same_instance(self):
        """シングルトンは同じインスタンスを返す"""
        from app.services.experiment_service import ExperimentService

        ExperimentService.reset_instance()
        instance1 = ExperimentService.get_instance()
        instance2 = ExperimentService.get_instance()

        assert instance1 is instance2

    def test_reset_instance(self):
        """インスタンスをリセットできる"""
        from app.services.experiment_service import ExperimentService

        ExperimentService.reset_instance()
        instance1 = ExperimentService.get_instance()
        ExperimentService.reset_instance()
        instance2 = ExperimentService.get_instance()

        assert instance1 is not instance2
