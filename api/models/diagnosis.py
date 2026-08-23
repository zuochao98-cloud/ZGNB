"""持仓诊断模型"""

from pydantic import BaseModel


class ExitSignalItem(BaseModel):
    signal_type: str = ""
    date: str = ""
    description: str = ""
    confidence: float = 0


class BuySignalItem(BaseModel):
    signal_type: str = ""
    date: str = ""
    description: str = ""
    confidence: float = 0
    action: str = ""


class DiagnosisResponse(BaseModel):
    ts_code: str
    name: str = ""
    price: float = 0
    trade_date: str = ""

    # 当前状态
    price_position: str = ""
    trend_status: str = ""

    # 指标快照
    kdj_j: float = 0
    macd_dif: float = 0
    macd_veto: bool = False
    bbi: float = 0
    white_line: float = 0
    yellow_line: float = 0
    is_gold_cross: bool = False
    is_dead_cross: bool = False

    # 防卖飞评分
    sell_score: int = 0
    sell_score_desc: str = ""
    sell_score_details: dict[str, bool] = {}

    # 出货 / 买入信号
    exit_signals: list[ExitSignalItem] = []
    buy_signals: list[BuySignalItem] = []

    # 主力阶段
    kirin_phase: str = "UNKNOWN"
    kirin_confidence: float = 0

    # 蜈蚣图
    is_centipede: bool = False
    centipede_score: float = 0

    # 牛绳
    bull_rope_status: str = ""
    bull_rope_gap_pct: float = 0

    # 沙漏
    sandglass_score: float = 0
    sandglass_is_perfect: bool = False

    # 止损 / 止盈
    stop_loss: float | None = None
    target_price: float | None = None

    # 综合
    recommendation: str = ""
    risk_level: str = "UNKNOWN"
