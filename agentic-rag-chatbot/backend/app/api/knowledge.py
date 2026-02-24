from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.jwt_handler import verify_token
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/api/admin/knowledge", tags=["knowledge"])


class DocumentMetadata(BaseModel):
    title: str = ""
    category: str = ""
    source: str = ""


class AddDocumentRequest(BaseModel):
    content: str = Field(..., min_length=1)
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)


class DocumentResponse(BaseModel):
    id: str
    content: str
    metadata: dict


class ListDocumentsResponse(BaseModel):
    success: bool
    data: dict


@router.get("", response_model=ListDocumentsResponse)
async def list_documents(
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
    token: dict = Depends(verify_token),
):
    """ドキュメント一覧を取得する"""
    service = KnowledgeService.get_instance()
    result = service.list_documents(category=category, limit=limit, offset=offset)
    return {"success": True, "data": result}


@router.get("/{doc_id}")
async def get_document(
    doc_id: str,
    token: dict = Depends(verify_token),
):
    """特定ドキュメントを取得する"""
    service = KnowledgeService.get_instance()
    doc = service.get_document(doc_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ドキュメントが見つかりません: {doc_id}",
        )
    return {"success": True, "data": doc}


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_document(
    request: AddDocumentRequest,
    token: dict = Depends(verify_token),
):
    """ドキュメントを追加する"""
    service = KnowledgeService.get_instance()
    doc = service.add_document(
        content=request.content,
        metadata=request.metadata.model_dump(),
    )
    return {"success": True, "data": doc}


@router.delete("/{doc_id}", status_code=status.HTTP_200_OK)
async def delete_document(
    doc_id: str,
    token: dict = Depends(verify_token),
):
    """ドキュメントを削除する"""
    service = KnowledgeService.get_instance()
    deleted = service.delete_document(doc_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ドキュメントが見つかりません: {doc_id}",
        )
    return {"success": True, "data": {"deleted": doc_id}}
