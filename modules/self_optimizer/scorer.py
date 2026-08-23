"""Trading score: 60% real monthly_reviews_self data + 40% LLM judge.

真实分公式 (0-60):
- 30% 月度平均胜率: clamp [-10%, +10%] → [0, 30]
- 30% 平均回撤反向: <10% 满分 30, >50% 零分, 10-50% 线性
- 40% 信号准确率: 0-100% 线性映射 0-40

LLM 分公式 (0-40):
- 由 llm_judge.paired_judge() 提供, 此处仅占位
"""

from __future__ import annotations

from typing import Any


def _score_return(avg_return: float) -> float:
    """胜率映射: [-10%, +10%] → [0, 30]."""
    clamped = max(-10.0, min(10.0, avg_return))
    return (clamped + 10.0) / 20.0 * 30.0


def _score_drawdown(avg_drawdown: float) -> float:
    """回撤反向: <10% 满分 30, >50% 零分."""
    if avg_drawdown < 10.0:
        return 30.0
    if avg_drawdown > 50.0:
        return 0.0
    return (50.0 - avg_drawdown) / 40.0 * 30.0


def _score_accuracy(accuracy_rate: float) -> float:
    """准确率: 0-100% → 0-40."""
    clamped = max(0.0, min(100.0, accuracy_rate))
    return clamped / 100.0 * 40.0


def compute_trading_score(monthly_stats: dict[str, Any]) -> float:
    """60% 真实数据分 (0-60)."""
    s_return = _score_return(monthly_stats["avg_return"])
    s_drawdown = _score_drawdown(monthly_stats["avg_drawdown"])
    s_accuracy = _score_accuracy(monthly_stats["accuracy_rate"])
    return min(60.0, s_return + s_drawdown + s_accuracy)


def compute_llm_score(proposed: dict[str, Any]) -> float:
    """40% LLM 评审分 (0-40).

    V1 stub: 返回中性 20 分. V1.1+ 由 llm_judge.paired_judge 实现.
    """
    return 20.0


def compute_total_score(
    review_month: str,
    monthly_stats: dict[str, Any],
    proposed: dict[str, Any],
) -> tuple[float, dict[str, float]]:
    """返回 (总分, 拆分) 总分 ∈ [0, 100]."""
    real = compute_trading_score(monthly_stats)
    llm = compute_llm_score(proposed)
    total = real + llm
    return total, {"real": real, "llm": llm, "total": total}
