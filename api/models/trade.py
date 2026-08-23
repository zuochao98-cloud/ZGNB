"""交易记录模型"""

from pydantic import BaseModel, Field


class TradeAddRequest(BaseModel):
    text: str = Field(description="口语化交易描述，如 '4月25号买了100股茅台，1800块'")


class TradeRecordResponse(BaseModel):
    id: int = 0
    ts_code: str = ""
    trade_date: str = ""
    action: str = ""
    price: float = 0
    quantity: int = 0
    amount: float = 0
    reason: str = ""
    signal_type: str = ""
    zg_review: str = ""
    tags: str = ""
    notes: str = ""


class TradeListResponse(BaseModel):
    total: int = 0
    page: int = 1
    page_size: int = 20
    records: list[TradeRecordResponse] = []


class TradeParseResult(BaseModel):
    success: bool
    confidence: float = 0
    data: dict | None = None
    missing_fields: list[str] = []
    error_message: str = ""


class TradeStatsResponse(BaseModel):
    summary: dict = {}
    pnl: dict = {}
