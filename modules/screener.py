"""Backward-compatibility shim for modules.screener package."""
# mypy: ignore-errors

from modules.screener import (
    StockScore,
    MarketStatus,
    get_all_stocks,
    get_recent_klines,
    analyze_stock,
    screen_stocks,
    format_stock_score,
    daily_workflow,
    is_perfect_pattern,
    score_b1_opportunity,
    score_trend,
    score_volume_pattern,
    score_risk,
    calculate_kdj,
    calculate_bbi,
    calculate_vol_ma,
)

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
]
