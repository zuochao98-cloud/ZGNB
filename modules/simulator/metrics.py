"""
专业回测绩效指标模块。

v3.9.0 迁移：实际实现已统一到 modules.core.metrics，本模块仅做 re-export。
"""

from ..core.metrics import (
    PerformanceMetrics,
    calculate_metrics,
    calculate_performance_metrics,
    daily_returns,
    compute_drawdown,
)

__all__ = [
    "PerformanceMetrics",
    "calculate_metrics",
    "calculate_performance_metrics",
    "daily_returns",
    "compute_drawdown",
]
