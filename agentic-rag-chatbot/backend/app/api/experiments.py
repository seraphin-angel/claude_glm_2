"""P3-55: A/Bテスト基盤 - 実験管理APIエンドポイント"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.jwt_handler import verify_token
from app.models.experiment import (
    ExperimentCreateRequest,
    ExperimentStatusUpdateRequest,
    VariantAssignRequest,
    MetricRecordRequest,
    ExperimentStatus,
)
from app.services.experiment_service import ExperimentService
from app.services.metrics_service import MetricsService
from app.services.statistics_service import StatisticsService

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


def _to_experiment_response(experiment) -> dict:
    """実験をレスポンス形式に変換する。"""
    return {
        "experiment_id": experiment.experiment_id,
        "name": experiment.name,
        "description": experiment.description,
        "variants": [
            {
                "variant_id": v.variant_id,
                "name": v.name,
                "weight": v.weight,
                "config": v.config,
            }
            for v in experiment.variants
        ],
        "status": experiment.status.value,
        "start_date": experiment.start_date.isoformat() if experiment.start_date else None,
        "end_date": experiment.end_date.isoformat() if experiment.end_date else None,
        "metrics": [m.value for m in experiment.metrics],
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_experiment(
    request: ExperimentCreateRequest,
    token: dict = Depends(verify_token),
) -> dict:
    """実験を作成する。"""
    service = ExperimentService.get_instance()
    try:
        experiment = service.create_experiment(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    return {
        "success": True,
        "data": _to_experiment_response(experiment),
    }


@router.get("")
async def list_experiments(
    status_filter: str = None,
    token: dict = Depends(verify_token),
) -> dict:
    """実験一覧を取得する。"""
    service = ExperimentService.get_instance()
    filter_status = None
    if status_filter:
        try:
            filter_status = ExperimentStatus(status_filter)
        except ValueError:
            pass
    experiments = service.list_experiments(status=filter_status)
    return {
        "success": True,
        "data": {
            "experiments": [_to_experiment_response(e) for e in experiments],
            "total": len(experiments),
        },
    }


@router.get("/{experiment_id}")
async def get_experiment(
    experiment_id: str,
    token: dict = Depends(verify_token),
) -> dict:
    """実験を取得する。"""
    service = ExperimentService.get_instance()
    experiment = service.get_experiment(experiment_id)
    if experiment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment '{experiment_id}' not found",
        )
    return {
        "success": True,
        "data": _to_experiment_response(experiment),
    }


@router.put("/{experiment_id}/status")
async def update_experiment_status(
    experiment_id: str,
    request: ExperimentStatusUpdateRequest,
    token: dict = Depends(verify_token),
) -> dict:
    """実験のステータスを更新する。"""
    service = ExperimentService.get_instance()
    try:
        experiment = service.update_status(experiment_id, request.status)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    return {
        "success": True,
        "data": _to_experiment_response(experiment),
    }


@router.post("/{experiment_id}/assign")
async def assign_variant(
    experiment_id: str,
    request: VariantAssignRequest,
    token: dict = Depends(verify_token),
) -> dict:
    """ユーザーにバリアントを割り当てる。"""
    service = ExperimentService.get_instance()
    try:
        variant_id = service.assign_variant(experiment_id, request.user_id)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
    return {
        "success": True,
        "data": {
            "experiment_id": experiment_id,
            "user_id": request.user_id,
            "variant_id": variant_id,
        },
    }


@router.post("/{experiment_id}/metrics")
async def record_metric(
    experiment_id: str,
    request: MetricRecordRequest,
    token: dict = Depends(verify_token),
) -> dict:
    """指標を記録する。"""
    metrics_service = MetricsService.get_instance()
    metric = metrics_service.record_metric(
        experiment_id=experiment_id,
        variant_id=request.variant_id,
        user_id=request.user_id,
        metric_type=request.metric_type,
        value=request.value,
    )
    return {
        "success": True,
        "data": {
            "experiment_id": metric.experiment_id,
            "variant_id": metric.variant_id,
            "user_id": metric.user_id,
            "metric_type": metric.metric_type.value,
            "value": metric.value,
            "timestamp": metric.timestamp.isoformat(),
        },
    }


@router.get("/{experiment_id}/results")
async def get_experiment_results(
    experiment_id: str,
    metric_type: str = "response_quality",
    token: dict = Depends(verify_token),
) -> dict:
    """実験結果を取得する。"""
    from app.models.experiment import MetricType

    exp_service = ExperimentService.get_instance()
    metrics_service = MetricsService.get_instance()
    stats_service = StatisticsService()

    experiment = exp_service.get_experiment(experiment_id)
    if experiment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment '{experiment_id}' not found",
        )

    try:
        metric_type_enum = MetricType(metric_type)
    except ValueError:
        metric_type_enum = MetricType.RESPONSE_QUALITY

    # 各バリアントの統計を取得
    variant_stats = metrics_service.get_variant_statistics(
        experiment_id=experiment_id,
        metric_type=metric_type_enum,
    )

    # 統計分析
    variant_ids = [v.variant_id for v in experiment.variants]
    if len(variant_ids) >= 2:
        control_metrics = [
            m.value for m in metrics_service.get_metrics(
                experiment_id=experiment_id,
                variant_id=variant_ids[0],
                metric_type=metric_type_enum,
            )
        ]
        treatment_metrics = [
            m.value for m in metrics_service.get_metrics(
                experiment_id=experiment_id,
                variant_id=variant_ids[1],
                metric_type=metric_type_enum,
            )
        ]
        comparison = stats_service.analyze_experiment(
            control_metrics=control_metrics,
            treatment_metrics=treatment_metrics,
        )
    else:
        comparison = {}

    return {
        "success": True,
        "data": {
            "experiment_id": experiment_id,
            "metric_type": metric_type_enum.value,
            "variants": variant_stats,
            "comparison": comparison.get("comparison", {}),
        },
    }
