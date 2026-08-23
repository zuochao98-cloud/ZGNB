"""modules.screener 包：选股与择时系统。"""

from .criteria import (
    _CRITERIA_REGISTRY,
    _check_centipede,
    _check_sandglass_min,
    _register,
)
from .data import _dict_to_daily, get_all_stocks, get_recent_klines
from .engine import _analyze_worker, _daily_to_dict, _filter_stock, analyze_stock, screen_stocks
from .format import format_stock_score
from .market import get_market_status
from .models import MarketStatus, StockScore
from .scoring import (
    calculate_bbi,
    calculate_kdj,
    calculate_vol_ma,
    is_perfect_pattern,
    score_b1_opportunity,
    score_risk,
    score_trend,
    score_volume_pattern,
)
from .workflow import daily_workflow

__all__ = [
    "StockScore",
    "MarketStatus",
    "get_all_stocks",
    "get_recent_klines",
    "analyze_stock",
    "screen_stocks",
    "format_stock_score",
    "daily_workflow",
    "is_perfect_pattern",
    "score_b1_opportunity",
    "score_trend",
    "score_volume_pattern",
    "score_risk",
    "calculate_kdj",
    "calculate_bbi",
    "calculate_vol_ma",
    "_CRITERIA_REGISTRY",
    "_register",
    "_check_centipede",
    "_check_sandglass_min",
    "_dict_to_daily",
    "_analyze_worker",
    "_filter_stock",
    "_daily_to_dict",
    "get_market_status",
]
