"""P3-54: ユーザー API エンドポイント"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.jwt_handler import verify_token, get_user_id_from_payload
from app.models.user import UserPlan, UserResponse, UserUpdatePlanRequest
from app.services.user_service import UserService

router = APIRouter(prefix="/api/users", tags=["users"])


async def get_current_user_id(payload: dict = Depends(verify_token)) -> str:
    """現在のユーザーIDを取得する"""
    user_id = get_user_id_from_payload(payload)
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="ユーザーIDがトークンに含まれていません",
        )
    return user_id


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user_id: str = Depends(get_current_user_id),
) -> UserResponse:
    """
    現在のユーザー情報を取得

    Returns:
        ユーザープロファイル
    """
    service = UserService.get_instance()
    profile = service.get_or_create_user(user_id)
    return UserResponse.from_profile(profile)


@router.get("/me/history")
async def get_conversation_history(
    limit: int = Query(default=10, ge=1, le=100),
    category: str | None = None,
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """
    現在のユーザーの会話履歴を取得

    Args:
        limit: 取得する最大件数
        category: フィルタするカテゴリ

    Returns:
        会話履歴のリスト
    """
    service = UserService.get_instance()
    
    # ユーザーが存在することを確認
    profile = service.get_user(user_id)
    if profile is None:
        return {"success": True, "history": []}
    
    history = service.get_conversation_history(
        user_id=user_id,
        limit=limit,
        category=category,
    )
    
    return {
        "success": True,
        "history": [h.model_dump() for h in history],
    }


@router.patch("/me/plan", response_model=UserResponse)
async def update_user_plan(
    request: UserUpdatePlanRequest,
    payload: dict = Depends(verify_token),
) -> UserResponse:
    """
    ユーザーのプランを更新（管理者のみ）

    管理者は target_user_id を指定して任意のユーザーのプランを変更できる。
    target_user_id が未指定の場合は、自分自身のプランを更新する。

    Args:
        request: プラン更新リクエスト（plan, target_user_id）

    Returns:
        更新されたユーザープロファイル

    Raises:
        HTTPException 403: 管理者権限がない場合
        HTTPException 401: ユーザーIDがトークンに含まれていない場合
    """
    # 管理者権限チェック: bool型のTrueのみ管理者として認める
    is_admin = payload.get("is_admin")
    if not (isinstance(is_admin, bool) and is_admin):
        raise HTTPException(
            status_code=403,
            detail="プランの変更は管理者のみ実行できます",
        )

    requester_user_id = get_user_id_from_payload(payload)
    if requester_user_id is None:
        raise HTTPException(status_code=401, detail="ユーザーIDがトークンに含まれていません")

    # target_user_id が指定された場合はそのユーザーを更新、未指定は自分自身
    target_user_id = request.target_user_id if request.target_user_id else requester_user_id

    service = UserService.get_instance()

    # ユーザーが存在することを確認
    profile = service.get_user(target_user_id)
    if profile is None:
        # ユーザーが存在しない場合は作成
        from app.models.user import UserCreateRequest
        service.create_user(UserCreateRequest(user_id=target_user_id))

    updated = service.update_user_plan(target_user_id, request.plan)
    return UserResponse.from_profile(updated)


@router.get("/me/recommendations")
async def get_user_recommendations(
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """
    ユーザーにパーソナライズされた推薦を取得

    Returns:
        推薦情報（FAQ、カテゴリなど）
    """
    from app.services.faq_service import FAQService
    
    user_service = UserService.get_instance()
    faq_service = FAQService.get_instance()
    
    profile = user_service.get_user(user_id)
    
    # パーソナライズされたFAQを取得
    recommended_faqs = faq_service.get_recommended_faqs(
        user_profile=profile,
        limit=5,
    )
    
    return {
        "success": True,
        "recommendations": {
            "faqs": recommended_faqs,
            "preferred_categories": list(profile.preferred_categories) if profile else [],
        },
    }
