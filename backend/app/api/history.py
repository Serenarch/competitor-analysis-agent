"""历史记录接口"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import HistoryResponse, HistoryItem
from app.services.report_service import get_report_service

router = APIRouter(prefix="/api/history", tags=["历史"])


@router.get("", response_model=HistoryResponse)
async def list_history(limit: int = 20):
    """列出历史报告"""
    service = get_report_service()
    items = service.list_all(limit=limit)
    return HistoryResponse(
        items=[HistoryItem(**item) for item in items],
        total=len(items),
    )


@router.delete("/{report_id}")
async def delete_history(report_id: str):
    """删除历史报告"""
    service = get_report_service()
    if service.delete(report_id):
        return {"success": True}
    raise HTTPException(404, "报告不存在")