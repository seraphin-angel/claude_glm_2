"""P3-55: A/Bテスト基盤 - Experiments API のテスト"""

import pytest
from httpx import AsyncClient, ASGITransport

# JWT_SECRET_KEY, DEBUG_MODE は conftest.py で一元管理


# ---------------------------------------------------------------------------
# Experiment API tests
# ---------------------------------------------------------------------------
class TestExperimentAPI:
    """実験APIのテスト"""

    @pytest.fixture(autouse=True)
    def reset_services(self):
        """各テスト前にサービスをリセット"""
        from app.services.experiment_service import ExperimentService
        from app.services.metrics_service import MetricsService
        ExperimentService.reset_instance()
        MetricsService.reset_instance()
        yield
        ExperimentService.reset_instance()
        MetricsService.reset_instance()

    @pytest.fixture
    def auth_headers(self) -> dict:
        """認証ヘッダー"""
        from app.auth.jwt_handler import create_access_token
        token = create_access_token({"sub": "admin-user", "role": "admin"})
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_create_experiment_api(self, auth_headers):
        """実験作成API"""
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/experiments",
                json={
                    "experiment_id": "test-exp-001",
                    "name": "Test Experiment",
                    "description": "A test experiment",
                    "variants": [
                        {"variant_id": "control", "name": "Control", "weight": 0.5},
                        {"variant_id": "treatment", "name": "Treatment", "weight": 0.5},
                    ],
                },
                headers=auth_headers,
            )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["experiment_id"] == "test-exp-001"

    @pytest.mark.asyncio
    async def test_list_experiments_api(self, auth_headers):
        """実験一覧API"""
        from app.main import app
        from app.services.experiment_service import ExperimentService
        from app.models.experiment import (
            ExperimentCreateRequest,
            VariantCreateRequest,
        )

        service = ExperimentService.get_instance()
        service.create_experiment(ExperimentCreateRequest(
            experiment_id="list-test",
            name="List Test",
            variants=[
                VariantCreateRequest(variant_id="control", name="Control", weight=0.5),
                VariantCreateRequest(variant_id="treatment", name="Treatment", weight=0.5),
            ],
        ))

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/experiments", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["experiments"]) >= 1

    @pytest.mark.asyncio
    async def test_get_experiment_api(self, auth_headers):
        """実験取得API"""
        from app.main import app
        from app.services.experiment_service import ExperimentService
        from app.models.experiment import (
            ExperimentCreateRequest,
            VariantCreateRequest,
        )

        service = ExperimentService.get_instance()
        service.create_experiment(ExperimentCreateRequest(
            experiment_id="get-test",
            name="Get Test",
            variants=[
                VariantCreateRequest(variant_id="control", name="Control", weight=0.5),
                VariantCreateRequest(variant_id="treatment", name="Treatment", weight=0.5),
            ],
        ))

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/experiments/get-test", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["experiment_id"] == "get-test"

    @pytest.mark.asyncio
    async def test_start_experiment_api(self, auth_headers):
        """実験開始API"""
        from app.main import app
        from app.services.experiment_service import ExperimentService
        from app.models.experiment import (
            ExperimentCreateRequest,
            VariantCreateRequest,
        )

        service = ExperimentService.get_instance()
        service.create_experiment(ExperimentCreateRequest(
            experiment_id="start-test",
            name="Start Test",
            variants=[
                VariantCreateRequest(variant_id="control", name="Control", weight=0.5),
                VariantCreateRequest(variant_id="treatment", name="Treatment", weight=0.5),
            ],
        ))

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.put(
                "/api/experiments/start-test/status",
                json={"status": "running"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "running"

    @pytest.mark.asyncio
    async def test_assign_variant_api(self, auth_headers):
        """バリアント割り当てAPI"""
        from app.main import app
        from app.services.experiment_service import ExperimentService
        from app.models.experiment import (
            ExperimentCreateRequest,
            VariantCreateRequest,
            ExperimentStatus,
        )

        service = ExperimentService.get_instance()
        service.create_experiment(ExperimentCreateRequest(
            experiment_id="assign-test",
            name="Assign Test",
            variants=[
                VariantCreateRequest(variant_id="control", name="Control", weight=0.5),
                VariantCreateRequest(variant_id="treatment", name="Treatment", weight=0.5),
            ],
        ))
        service.update_status("assign-test", ExperimentStatus.RUNNING)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/experiments/assign-test/assign",
                json={"user_id": "user-123"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["variant_id"] in ["control", "treatment"]

    @pytest.mark.asyncio
    async def test_record_metric_api(self, auth_headers):
        """指標記録API"""
        from app.main import app
        from app.services.experiment_service import ExperimentService
        from app.models.experiment import (
            ExperimentCreateRequest,
            VariantCreateRequest,
            ExperimentStatus,
            MetricType,
        )

        service = ExperimentService.get_instance()
        service.create_experiment(ExperimentCreateRequest(
            experiment_id="metric-test",
            name="Metric Test",
            variants=[
                VariantCreateRequest(variant_id="control", name="Control", weight=0.5),
                VariantCreateRequest(variant_id="treatment", name="Treatment", weight=0.5),
            ],
        ))
        service.update_status("metric-test", ExperimentStatus.RUNNING)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/experiments/metric-test/metrics",
                json={
                    "variant_id": "control",
                    "user_id": "user-123",
                    "metric_type": "response_quality",
                    "value": 4.5,
                },
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_results_api(self, auth_headers):
        """実験結果取得API"""
        from app.main import app
        from app.services.experiment_service import ExperimentService
        from app.services.metrics_service import MetricsService
        from app.models.experiment import (
            ExperimentCreateRequest,
            VariantCreateRequest,
            ExperimentStatus,
            MetricType,
        )

        exp_service = ExperimentService.get_instance()
        metrics_service = MetricsService.get_instance()

        exp_service.create_experiment(ExperimentCreateRequest(
            experiment_id="results-test",
            name="Results Test",
            variants=[
                VariantCreateRequest(variant_id="control", name="Control", weight=0.5),
                VariantCreateRequest(variant_id="treatment", name="Treatment", weight=0.5),
            ],
        ))
        exp_service.update_status("results-test", ExperimentStatus.RUNNING)

        # 指標を記録
        for i in range(5):
            metrics_service.record_metric(
                experiment_id="results-test",
                variant_id="control",
                user_id=f"control-user-{i}",
                metric_type=MetricType.RESPONSE_QUALITY,
                value=3.0 + i,
            )
            metrics_service.record_metric(
                experiment_id="results-test",
                variant_id="treatment",
                user_id=f"treatment-user-{i}",
                metric_type=MetricType.RESPONSE_QUALITY,
                value=4.0 + i,
            )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/experiments/results-test/results",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "control" in data["data"]["variants"]
        assert "treatment" in data["data"]["variants"]
        assert "comparison" in data["data"]
