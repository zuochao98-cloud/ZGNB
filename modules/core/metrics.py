"""
绩效指标计算公共逻辑（v3.9.0 技术债务清理）

统一的绩效指标计算模块，供 simulator/metrics.py、verify/pipeline.py 及其他模块使用。
包含完整的 20 字段 PerformanceMetrics 与 calculate_metrics 函数。
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any

# 每年交易日数（A 股年化因子统一常量）
TRADING_DAYS_PER_YEAR = 252


@dataclass
class PerformanceMetrics:
    """专业回测绩效指标（20 字段）。"""

    # 收益类
    total_return: float = 0.0  # 总收益率
    annualized_return: float = 0.0  # 年化收益率
    benchmark_return: float = 0.0  # 基准收益率
    alpha: float = 0.0  # Jensen's alpha（年化）
    beta: float = 0.0  # 市场 beta

    # 风险调整收益
    sharpe_ratio: float = 0.0  # 夏普比率
    sortino_ratio: float = 0.0  # 索提诺比率
    calmar_ratio: float = 0.0  # 卡尔玛比率
    max_drawdown: float = 0.0  # 最大回撤（正值）
    max_drawdown_duration: int = 0  # 最长回撤持续天数

    # 交易统计
    win_rate: float = 0.0  # 胜率
    profit_factor: float = 0.0  # 盈亏比（总盈利/总亏损）
    avg_win: float = 0.0  # 平均盈利
    avg_loss: float = 0.0  # 平均亏损（正值）
    gain_loss_ratio: float = 0.0  # 盈亏比（avg_win / avg_loss）
    max_consecutive_wins: int = 0  # 最大连胜
    max_consecutive_losses: int = 0  # 最大连亏

    # 波动率
    volatility_annual: float = 0.0  # 年化波动率

    # 兼容字段（原 core 独有）
    total_trades: int = 0  # 总交易次数
    avg_holding_days: float = 0.0  # 平均持仓天数


def daily_returns(values: list[float]) -> list[float]:
    """
    从序列计算日收益率（v3.9.0 提取自 simulator/metrics.py）。

    当前值与前值之差除以前值，前值为 0 时记为 0。
    """
    rets: list[float] = []
    for i in range(1, len(values)):
        prev = values[i - 1]
        cur = values[i]
        if prev == 0:
            rets.append(0.0)
        else:
            rets.append((cur - prev) / prev)
    return rets


def compute_sharpe(returns: list[float], periods_per_year: float = TRADING_DAYS_PER_YEAR) -> float:
    """计算夏普比率（sample std，不减无风险利率）。

    Args:
        returns: 收益率序列（日收益率或其他频率）。
        periods_per_year: 年化因子，默认 252（A 股交易日）。

    Returns:
        年化夏普比率；序列长度不足或标准差为零时返回 0.0。
    """
    if len(returns) < 2:
        return 0.0
    avg_ret = sum(returns) / len(returns)
    variance = sum((r - avg_ret) ** 2 for r in returns) / (len(returns) - 1)
    std_ret = variance**0.5
    if std_ret > 0:
        return (avg_ret / std_ret) * (periods_per_year**0.5)
    return 0.0


def compute_drawdown(values: list[float]) -> tuple[float, int]:
    """
    计算最大回撤与最长回撤持续时间（v3.9.0 提取自 simulator/metrics.py）。

    最大回撤以正值返回（如 0.05 表示回撤 5%）。
    持续时间为「高点 → 下一个新高点」之间的最长交易日数。
    """
    if not values:
        return 0.0, 0

    peak = values[0]
    peak_idx = 0
    max_dd = 0.0
    max_duration = 0

    for i, val in enumerate(values):
        if val > peak:
            duration = i - peak_idx
            if duration > max_duration:
                max_duration = duration
            peak = val
            peak_idx = i

        dd = (peak - val) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    return max_dd, max_duration


def calculate_metrics(
    equity_curve: list[dict[str, Any]],
    benchmark_curve: list[dict[str, Any]],
    trades: list[Any],
) -> PerformanceMetrics:
    """
    计算回测绩效指标。

    计算口径：
    - 波动率与夏普/索提诺使用 sample std（``statistics.stdev``）
    - 夏普/索提诺不减无风险利率
    - 支持 benchmark 曲线计算 alpha/beta
    - 交易统计仅统计 SELL 动作的成交

    Args:
        equity_curve: 资金曲线，每个元素至少包含 ``date`` 与 ``equity``。
        benchmark_curve: 基准曲线，每个元素至少包含 ``date`` 与 ``close``。
        trades: 成交记录列表，通常为 ``TradeRecord`` 序列。

    Returns:
        PerformanceMetrics: 各项绩效指标。
    """
    metrics = PerformanceMetrics()

    if not equity_curve:
        return metrics

    equities = [float(p.get("equity", 0)) for p in equity_curve]
    initial = equities[0]
    final = equities[-1]

    if initial > 0:
        metrics.total_return = (final / initial) - 1.0

    n_periods = len(equity_curve) - 1
    if n_periods > 0 and initial > 0:
        metrics.annualized_return = (final / initial) ** (TRADING_DAYS_PER_YEAR / n_periods) - 1.0

    daily_rets = daily_returns(equities)

    # 年化波动率
    if len(daily_rets) > 1:
        metrics.volatility_annual = statistics.stdev(daily_rets) * math.sqrt(TRADING_DAYS_PER_YEAR)

    # 夏普比率（不减无风险利率）
    metrics.sharpe_ratio = compute_sharpe(daily_rets)

    # 索提诺比率：仅使用负收益计算下行标准差
    if daily_rets:
        avg_ret = sum(daily_rets) / len(daily_rets)
        negative_rets = [r for r in daily_rets if r < 0]
        std_neg = statistics.stdev(negative_rets) if len(negative_rets) > 1 else 0.0
        if std_neg > 0:
            metrics.sortino_ratio = (avg_ret / std_neg) * math.sqrt(TRADING_DAYS_PER_YEAR)
        elif avg_ret > 0:
            # 无下行波动但平均收益为正，按正无穷表示
            metrics.sortino_ratio = float("inf")

    # 最大回撤与持续时间
    max_dd, max_duration = compute_drawdown(equities)
    metrics.max_drawdown = max_dd
    metrics.max_drawdown_duration = max_duration

    # Calmar 比率
    if metrics.max_drawdown != 0:
        metrics.calmar_ratio = metrics.annualized_return / abs(metrics.max_drawdown)

    # 基准收益与 beta/alpha
    if benchmark_curve:
        bench_values = [float(p.get("close", 0)) for p in benchmark_curve]
        if bench_values and bench_values[0] > 0:
            metrics.benchmark_return = (bench_values[-1] / bench_values[0]) - 1.0

        bench_rets = daily_returns(bench_values)
        if len(daily_rets) == len(bench_rets) and len(daily_rets) > 1:
            try:
                slope, intercept = statistics.linear_regression(bench_rets, daily_rets)
                metrics.beta = slope
                # alpha 为日超额收益，年化后更直观
                metrics.alpha = intercept * TRADING_DAYS_PER_YEAR
            except statistics.StatisticsError:
                metrics.beta = 0.0
                metrics.alpha = 0.0

    # 交易统计（仅 SELL 成交）
    sell_trades = [t for t in trades if getattr(t, "action", None) == "SELL"]
    if sell_trades:
        pnls = [float(getattr(t, "pnl", 0)) for t in sell_trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        metrics.win_rate = len(wins) / len(pnls) if pnls else 0.0

        total_profit = sum(wins)
        total_loss = abs(sum(losses))
        metrics.profit_factor = total_profit / total_loss if total_loss > 0 else float("inf")

        metrics.avg_win = statistics.mean(wins) if wins else 0.0
        metrics.avg_loss = abs(statistics.mean(losses)) if losses else 0.0
        metrics.gain_loss_ratio = metrics.avg_win / metrics.avg_loss if metrics.avg_loss > 0 else 0.0

        # 最大连胜 / 连亏
        max_wins = 0
        max_losses = 0
        cur_wins = 0
        cur_losses = 0
        for pnl in pnls:
            if pnl > 0:
                cur_wins += 1
                cur_losses = 0
                if cur_wins > max_wins:
                    max_wins = cur_wins
            else:
                cur_losses += 1
                cur_wins = 0
                if cur_losses > max_losses:
                    max_losses = cur_losses
        metrics.max_consecutive_wins = max_wins
        metrics.max_consecutive_losses = max_losses

    metrics.total_trades = len(sell_trades)

    # 平均持仓天数（兼容字段）
    holding_days_list = [getattr(t, "holding_days", 0) for t in sell_trades]
    if holding_days_list:
        metrics.avg_holding_days = sum(holding_days_list) / len(holding_days_list)

    return metrics


def calculate_performance_metrics(
    equity_curve: list[float],
    trades: list[dict] | None = None,
    risk_free_rate: float = 0.03,
    periods_per_year: int = 252,
) -> PerformanceMetrics:
    """
    兼容别名：将简单接口转换为 ``calculate_metrics`` 格式后调用。

    注意：此函数保持旧接口签名不变，但返回类型为新的 20 字段 PerformanceMetrics。
    计算口径以 ``calculate_metrics`` 为准（sample std、不减无风险利率）。

    Args:
        equity_curve: 资金曲线（按时间顺序的浮点数列表）
        trades: 交易记录列表（可选，每个元素为 dict，含 ``pnl`` 等键）
        risk_free_rate: 无风险利率（保留参数，实际不参与计算）
        periods_per_year: 每年的周期数（保留参数，实际使用 252）

    Returns:
        PerformanceMetrics
    """
    # 将 float 列表转换为 dict 列表以适配 calculate_metrics 接口
    eq_dicts = [{"equity": v} for v in equity_curve]

    # 将 dict trades 转换为带 action 属性的对象
    class _TradeProxy:
        """轻量代理，让 dict 形式的 trade 可被 calculate_metrics 消费。"""

        def __init__(self, d: dict) -> None:
            self.action = d.get("action", "SELL")
            self.pnl = d.get("pnl", 0)
            self.holding_days = d.get("holding_days", 0)

    trade_objs = [_TradeProxy(t) for t in trades] if trades else []

    return calculate_metrics(eq_dicts, [], trade_objs)


__all__ = [
    "TRADING_DAYS_PER_YEAR",
    "PerformanceMetrics",
    "calculate_metrics",
    "calculate_performance_metrics",
    "compute_sharpe",
    "daily_returns",
    "compute_drawdown",
]
