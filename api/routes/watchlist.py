"""自选股管理路由"""

from fastapi import APIRouter, HTTPException, Query

from api.models.watchlist import (
    WatchlistAddRequest,
    WatchlistListResponse,
    WatchlistScanResponse,
    WatchlistReportResponse,
)
from api.models.common import StatusResponse
from api.services import watchlist_service

router = APIRouter()


@router.get("/", response_model=WatchlistListResponse)
def list_watchlist(tags: str | None = Query(default=None)):
    """列出自选股"""
    try:
        return watchlist_service.list_watchlist(tags=tags)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取列表失败: {e}")


@router.post("/", response_model=StatusResponse)
def add_watchlist(req: WatchlistAddRequest):
    """添加到自选股"""
    try:
        result = watchlist_service.add_to_watchlist(req.ts_code, req.tags, req.notes)
        return StatusResponse(status="ok", message=f"已添加 {req.ts_code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加失败: {e}")


@router.delete("/{ts_code}", response_model=StatusResponse)
def remove_watchlist(ts_code: str):
    """从自选股移除"""
    try:
        result = watchlist_service.remove_from_watchlist(ts_code)
        return StatusResponse(status=result["status"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {e}")


@router.post("/scan", response_model=WatchlistScanResponse)
def scan_watchlist():
    """扫描自选股信号"""
    try:
        return watchlist_service.scan_watchlist()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"扫描失败: {e}")


@router.get("/report", response_model=WatchlistReportResponse)
def get_report():
    """生成日报"""
    try:
        return watchlist_service.generate_report()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成报告失败: {e}")
