"""自选股模型"""

from pydantic import BaseModel


class WatchlistAddRequest(BaseModel):
    ts_code: str
    tags: str = ""
    notes: str = ""


class WatchlistItem(BaseModel):
    id: int = 0
    ts_code: str
    name: str = ""
    tags: str = ""
    notes: str = ""
    added_date: str = ""
    alert_enabled: bool = True


class WatchlistListResponse(BaseModel):
    count: int
    items: list[WatchlistItem] = []


class WatchAlertItem(BaseModel):
    ts_code: str
    name: str = ""
    alert_type: str = ""
    level: str = ""
    message: str = ""


class WatchlistScanResponse(BaseModel):
    total: int = 0
    b1_count: int = 0
    b2_count: int = 0
    exit_count: int = 0
    break_count: int = 0
    abnormal_count: int = 0
    alerts: list[WatchAlertItem] = []


class WatchlistReportResponse(BaseModel):
    report: str
