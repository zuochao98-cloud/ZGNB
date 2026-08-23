#!/usr/bin/env python3
"""
仓位管理模块。

基于单笔风险（risk_per_trade）和止损幅度计算买入股数。
公式：shares = (equity * risk_pct) / (entry_price - stop_loss)
支持 ATR 风险扩展、最大持仓比例限制、现金利用率限制。
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from modules.indicators import DailyData

from . import Position, SimulationConfig
from ..constants import SIMULATOR_MAX_RISK_PER_TRADE_PCT

if TYPE_CHECKING:
    from collections.abc import Sequence


def _calculate_atr(klines: Sequence[DailyData], window: int) -> float:
    """
    计算最近 window 天的真实波动幅度均值（ATR）。

    Args:
        klines: 按日期排序的 K 线序列，长度至少为 window + 1
        window: 计算窗口

    Returns:
        ATR 值
    """
    true_ranges: list[float] = []
    for i in range(-window, 0):
        current = klines[i]
        previous = klines[i - 1]
        tr = max(
            current.high - current.low,
            abs(current.high - previous.close),
            abs(current.low - previous.close),
        )
        true_ranges.append(tr)
    return sum(true_ranges) / len(true_ranges)


def calculate_position_size(
    equity: float,
    entry_price: float,
    stop_loss: float,
    cash: float,
    config: SimulationConfig,
    klines: Sequence[DailyData] | None = None,
) -> tuple[int, float]:
    """
    计算应买入股数与承担的风险金额。

    Args:
        equity: 当前账户净值
        entry_price: 计划买入价
        stop_loss: 止损价
        cash: 可用现金
        config: 模拟配置
        klines: 可选，用于 ATR 仓位计算的近期 K 线

    Returns:
        (shares, risk_amount)
    """
    if entry_price <= 0 or stop_loss <= 0 or entry_price <= stop_loss:
        return 0, 0.0

    risk_pct = max(config.risk_per_trade_min, min(config.risk_per_trade, SIMULATOR_MAX_RISK_PER_TRADE_PCT))
    risk_amount = equity * risk_pct

    # 确定每股风险
    fixed_risk = entry_price - stop_loss
    if config.use_atr_sizing and klines is not None and len(klines) >= config.atr_window + 1:
        atr = _calculate_atr(klines, config.atr_window)
        risk_per_share = max(fixed_risk, atr * 0.5)
    else:
        risk_per_share = fixed_risk

    shares = int(math.floor(risk_amount / risk_per_share))

    # A股最小交易单位 100 股
    shares = (shares // 100) * 100
    if shares < 100:
        return 0, 0.0

    # 最大持仓比例限制
    max_value = equity * config.max_position_pct
    max_shares_by_value = int(max_value / entry_price / 100) * 100
    shares = min(shares, max_shares_by_value)

    if shares < 100:
        return 0, 0.0

    # 现金利用率限制
    max_cost = cash * config.cash_utilization_limit
    max_shares_by_cash = int(max_cost / entry_price / 100) * 100
    shares = min(shares, max_shares_by_cash)

    if shares < 100:
        return 0, 0.0

    actual_risk = shares * risk_per_share
    return shares, actual_risk


def build_position(
    ts_code: str,
    name: str,
    entry_date: str,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    cash: float,
    equity: float,
    config: SimulationConfig,
    klines: Sequence[DailyData] | None = None,
    can_sell_date: str = "",
    is_st: bool = False,
) -> Position | None:
    """
    构建一个持仓头寸。

    Args:
        ts_code: 股票代码
        name: 股票名称
        entry_date: 买入日期
        entry_price: 买入价
        stop_loss: 止损价
        take_profit: 止盈价
        cash: 可用现金
        equity: 当前账户净值
        config: 模拟配置
        klines: 可选，ATR 计算所需的近期 K 线
        can_sell_date: 最早可卖出日（T+1 制度）
        is_st: 是否为 ST/*ST 股票

    Returns:
        Position or None（若资金不足或止损无效）
    """
    shares, risk_amount = calculate_position_size(equity, entry_price, stop_loss, cash, config, klines=klines)
    if shares <= 0:
        return None

    amount = shares * entry_price
    commission = max(amount * config.cost_model.commission_rate, config.cost_model.min_commission)

    return Position(
        ts_code=ts_code,
        name=name,
        entry_date=entry_date,
        entry_price=entry_price,
        shares=shares,
        stop_loss=stop_loss,
        take_profit=take_profit,
        risk_amount=risk_amount,
        can_sell_date=can_sell_date,
        entry_commission=round(commission, 2),
        is_st=is_st,
    )
