"""Backward-compatibility shim for modules.data_sync package.

All implementation has moved to modules.data_sync/ subpackage.
Import from this top-level module remains supported.
"""
# mypy: ignore-errors

from modules.data_sync import (
    DataSyncer,
    _RateLimiter,
    _GLOBAL_LIMITER,
    _rate_limit_global,
    _compute_day_indicators,
    _build_indicator_row,
    _INDICATOR_INSERT_COLUMNS,
)

__all__ = [
    "DataSyncer",
    "_RateLimiter",
    "_GLOBAL_LIMITER",
    "_rate_limit_global",
    "_compute_day_indicators",
    "_build_indicator_row",
    "_INDICATOR_INSERT_COLUMNS",
]
