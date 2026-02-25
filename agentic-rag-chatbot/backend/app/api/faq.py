"""FAQ API エンドポイント"""

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.faq_service import FAQService

router = APIRouter(prefix="/api/faq", tags=["faq"])

# シングルトンインスタンスを取得
faq_service = FAQService.get_instance()


class FAQClickRequest(BaseModel):
    """FAQ クリックリクエスト"""

    faq_id: str


class APIResponse(BaseModel):
    """API レスポンス"""

    success: bool = True
    faqs: list[dict[str, Any]] = []
    categories: list[str] = []


@router.get("/suggestions")
async def get_faq_suggestions(
    page_url: str = Query(default="", description="現在のページURL"),
    limit: int = Query(default=3, ge=1, le=10, description="取得するFAQ数"),
) -> dict[str, Any]:
    """
    ページURLに基づくFAQ推薦を取得

    Args:
        page_url: 現在のページURL
        limit: 取得するFAQの最大数

    Returns:
        関連FAQのリスト
    """
    faqs = faq_service.get_faqs_by_page(page_url, limit=limit)
    return {"success": True, "faqs": faqs}


@router.get("/top")
async def get_top_faqs(
    limit: int = Query(default=5, ge=1, le=20, description="取得するFAQ数"),
    since_days: int = Query(default=7, ge=1, le=30, description="集計期間（日数）"),
) -> dict[str, Any]:
    """
    トップ質問を取得（閲覧数順）

    Args:
        limit: 取得するFAQの最大数
        since_days: 集計期間（日数）

    Returns:
        閲覧数順のFAQリスト
    """
    faqs = faq_service.get_top_questions(since_days=since_days, limit=limit)
    return {"success": True, "faqs": faqs}


@router.get("/search")
async def search_faqs(
    q: str = Query(default="", description="検索クエリ"),
    limit: int = Query(default=5, ge=1, le=20, description="取得するFAQ数"),
) -> dict[str, Any]:
    """
    FAQをキーワードで検索

    Args:
        q: 検索クエリ
        limit: 取得するFAQの最大数

    Returns:
        マッチしたFAQのリスト
    """
    if not q:
        return {"success": True, "faqs": []}

    faqs = faq_service.search_faqs(q, limit=limit)
    return {"success": True, "faqs": faqs}


@router.get("/categories")
async def get_categories() -> dict[str, Any]:
    """
    すべてのカテゴリを取得

    Returns:
        カテゴリのリスト
    """
    categories = faq_service.get_all_categories()
    return {"success": True, "categories": categories}


@router.post("/click")
async def record_faq_click(request: FAQClickRequest) -> dict[str, Any]:
    """
    FAQ クリックを記録（閲覧数を増やす）

    Args:
        request: クリックリクエスト

    Returns:
        成功レスポンス
    """
    faq_service.increment_view_count(request.faq_id)
    return {"success": True}
