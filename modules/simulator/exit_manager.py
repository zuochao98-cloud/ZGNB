#!/usr/bin/env python3
"""
退出管理模块。

负责每日检查持仓是否需要退出：
- 止损：收盘价跌破入场日最低价（或 N 型结构前低）
- 止盈（卤煮）：达到固定 R/R 后减半
- 移动止盈：收盘价跌破 20MA 或白线死叉黄线
"""

from __future__ import annotations

from ..indicators import DailyData, calculate_zg_white, calculate_dg_yellow, calculate_ma
from . import Position, SimulationConfig
from .execution_constraints import TradeConstraints


def _stop_loss_hit(position: Position, kline: DailyData) -> bool:
    """收盘价跌破止损位"""
    return kline.close < position.stop_loss


def _take_profit_hit(position: Position, kline: DailyData, rr: float) -> bool:
    """达到固定盈亏比（如 2R）"""
    risk = position.entry_price - position.stop_loss
    if risk <= 0:
        return False
    target = position.entry_price + risk * rr
    return kline.close >= target


def _trailing_stop_hit(klines: list[DailyData], position: Position, ma_days: int = 20) -> bool:
    """收盘价跌破 20MA 或白线死叉黄线"""
    if len(klines) < ma_days + 5:
        return False

    ma_value = calculate_ma([k.close for k in klines], ma_days)
    if klines[-1].close < ma_value:
        return True

    white = calculate_zg_white(klines)
    yellow = calculate_dg_yellow(klines)
    prev_white = calculate_zg_white(klines[:-1])
    prev_yellow = calculate_dg_yellow(klines[:-1])

    # 白线在黄线之上 → 死叉
    if prev_white >= prev_yellow and white < yellow:
        return True

    return False


def _record_hold_reason(position: Position, reason: str) -> None:
    """在持仓备注中记录 HOLD 原因，便于调用方识别 HOLD_T1 / HOLD_LIMIT 语义。"""
    position.notes.append(reason)


def check_exit(
    position: Position,
    klines: list[DailyData],
    config: SimulationConfig,
    constraints: TradeConstraints | None = None,
) -> tuple[str, int]:
    """
    检查持仓当日退出状态。

    Args:
        position: 持仓
        klines: 截至当前日期的 K 线（含当前日）
        config: 配置
        constraints: 当日交易约束，若为 None 则跳过涨跌停/停牌判断

    Returns:
        (action, shares_to_sell)
        action: "HOLD" / "STOP_LOSS" / "TAKE_PROFIT_PARTIAL" / "TRAILING_EXIT"
        shares_to_sell: 卖出股数（HOLD 时为 0，部分卖出时为半数）

    约束优先级高于止损/止盈：
    - 当 config.t1_lock 为 True 且当前日期 < position.can_sell_date 时，强制 HOLD。
    - 当 constraints 存在且 constraints.can_sell 为 False 时（如跌停），强制 HOLD。
    """
    if not klines:
        return "HOLD", 0

    current = klines[-1]

    # 1. T+1 锁定：A 股当日买入最早下一交易日才能卖出
    if config.t1_lock and current.trade_date < position.can_sell_date:
        _record_hold_reason(position, f"T+1锁定，当前 {current.trade_date} 最早可卖出日为 {position.can_sell_date}")
        return "HOLD", 0

    # 2. 交易约束（涨跌停、停牌等）阻止卖出
    if constraints is not None and not constraints.can_sell:
        _record_hold_reason(position, f"交易约束阻止卖出：{constraints.reason}")
        return "HOLD", 0

    # 3. 止损最高优先级
    if _stop_loss_hit(position, current):
        return "STOP_LOSS", position.shares

    # 4. 卤煮：达到固定 R/R 且尚未减半
    if not position.partial_exited and _take_profit_hit(position, current, config.partial_take_profit_rr):
        half = (position.shares // 2 // 100) * 100
        if half < 100:
            half = position.shares
        return "TAKE_PROFIT_PARTIAL", half

    # 5. 移动止盈：跌破 20MA 或白线死叉
    if _trailing_stop_hit(klines, position, config.trailing_ma_days):
        return "TRAILING_EXIT", position.shares

    return "HOLD", 0
