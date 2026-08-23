#!/usr/bin/env python3
"""
成交模拟模块。

- 买入：下一交易日开盘价 + 滑点
- 卖出：下一交易日收盘价 - 滑点
- 手续费：按配置比例双向收取
"""

from __future__ import annotations

from ..indicators import DailyData
from . import Position, SimulationConfig, TradeRecord
from .cost_model import calculate_costs
from .slippage_model import calculate_slippage


def _apply_slippage_buy(price: float, slippage: float) -> float:
    """买入滑点：提高成交价"""
    return price * (1 + slippage)


def _apply_slippage_sell(price: float, slippage: float) -> float:
    """卖出滑点：降低成交价"""
    return price * (1 - slippage)


def execute_buy(
    position: Position,
    kline: DailyData,
    config: SimulationConfig,
    klines: list[DailyData] | None = None,
) -> TradeRecord:
    """
    模拟买入成交。

    Args:
        position: 待买入头寸
        kline: 买入日 K 线
        config: 配置
        klines: 历史 K 线序列，用于动态滑点

    Returns:
        TradeRecord
    """
    slippage = calculate_slippage(kline, klines or [], "BUY", config)
    fill_price = _apply_slippage_buy(kline.open, slippage)
    amount = fill_price * position.shares
    costs = calculate_costs(amount, "BUY", config.cost_model)
    position.entry_commission = costs["total"]

    return TradeRecord(
        ts_code=position.ts_code,
        name=position.name,
        action="BUY",
        date=kline.trade_date,
        price=round(fill_price, 3),
        shares=position.shares,
        reason=f"B1信号入场，止损{position.stop_loss:.2f}",
        fee=costs["total"],
        stamp_duty=costs["stamp_duty"],
        transfer_fee=costs["transfer_fee"],
        notes=["买入成交"],
    )


def execute_sell(
    position: Position,
    kline: DailyData,
    config: SimulationConfig,
    reason: str,
    klines: list[DailyData] | None = None,
) -> TradeRecord:
    """
    模拟卖出成交。

    Args:
        position: 持仓
        kline: 卖出日 K 线
        config: 配置
        reason: 卖出原因
        klines: 历史 K 线序列，用于动态滑点

    Returns:
        TradeRecord
    """
    slippage = calculate_slippage(kline, klines or [], "SELL", config)
    fill_price = _apply_slippage_sell(kline.close, slippage)
    amount = fill_price * position.shares
    sell_costs = calculate_costs(amount, "SELL", config.cost_model)

    cost = position.entry_price * position.shares
    total_cost = sell_costs["total"] + position.entry_commission
    pnl = amount - cost - total_cost
    pnl_pct = pnl / cost if cost else 0.0

    return TradeRecord(
        ts_code=position.ts_code,
        name=position.name,
        action="SELL",
        date=kline.trade_date,
        price=round(fill_price, 3),
        shares=position.shares,
        pnl=round(pnl, 2),
        pnl_pct=round(pnl_pct, 4),
        reason=reason,
        fee=sell_costs["total"],
        stamp_duty=sell_costs["stamp_duty"],
        transfer_fee=sell_costs["transfer_fee"],
        notes=["卖出成交"],
    )


def execute_partial_sell(
    position: Position,
    kline: DailyData,
    config: SimulationConfig,
    sell_shares: int,
    reason: str,
    klines: list[DailyData] | None = None,
) -> TradeRecord:
    """
    模拟部分卖出（卤煮减半）。

    Args:
        position: 持仓
        kline: 卖出日 K 线
        config: 配置
        sell_shares: 卖出股数
        reason: 卖出原因
        klines: 历史 K 线序列，用于动态滑点

    Returns:
        TradeRecord
    """
    slippage = calculate_slippage(kline, klines or [], "PARTIAL_SELL", config)
    fill_price = _apply_slippage_sell(kline.close, slippage)
    amount = fill_price * sell_shares
    sell_costs = calculate_costs(amount, "PARTIAL_SELL", config.cost_model)

    cost_basis = position.entry_price * sell_shares
    ratio = sell_shares / position.shares if position.shares else 0.0
    proportional_buy_cost = position.entry_commission * ratio
    total_cost = sell_costs["total"] + proportional_buy_cost
    pnl = amount - cost_basis - total_cost
    pnl_pct = pnl / cost_basis if cost_basis else 0.0

    return TradeRecord(
        ts_code=position.ts_code,
        name=position.name,
        action="PARTIAL_SELL",
        date=kline.trade_date,
        price=round(fill_price, 3),
        shares=sell_shares,
        pnl=round(pnl, 2),
        pnl_pct=round(pnl_pct, 4),
        reason=reason,
        fee=sell_costs["total"],
        stamp_duty=sell_costs["stamp_duty"],
        transfer_fee=sell_costs["transfer_fee"],
        notes=["部分卖出成交"],
    )
