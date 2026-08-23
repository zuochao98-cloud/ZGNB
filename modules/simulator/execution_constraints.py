#!/usr/bin/env python3
"""
A 股交易约束层。

判断某只股票在指定交易日是否允许买入/卖出，包括：
- 涨跌停：主板 ±10%，科创/创业板 ±20%，ST ±5%
- 停牌：成交量与成交额均为 0 且价格无变化
- ST 过滤：默认不允许买入 ST/*ST/退市
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from ..indicators import DailyData
from ..constants import (
    SIMULATOR_GEM_STAR_PRICE_LIMIT_PCT,
    SIMULATOR_MAIN_BOARD_PRICE_LIMIT_PCT,
    SIMULATOR_ST_PRICE_LIMIT_PCT,
)


@dataclass
class TradeConstraints:
    """某股票在某交易日的交易约束快照"""

    can_buy: bool
    can_sell: bool
    reason: str
    price_limit: float | None = None
    price_floor: float | None = None
    is_st: bool = False
    is_halted: bool = False


def _is_st_name(name: str | None) -> bool:
    """通过名称判断是否 ST/*ST/退市。"""
    if not name:
        return False
    upper = name.upper()
    return "ST" in upper or "退" in name


def _limit_pct(ts_code: str, is_st: bool) -> float:
    """返回涨跌停幅度。"""
    if is_st:
        return SIMULATOR_ST_PRICE_LIMIT_PCT
    if ts_code.startswith("688") or ts_code.startswith("300") or ts_code.startswith("301"):
        return SIMULATOR_GEM_STAR_PRICE_LIMIT_PCT
    # 主板默认
    return SIMULATOR_MAIN_BOARD_PRICE_LIMIT_PCT


def _price_limits(prev_close: float, ts_code: str, is_st: bool) -> tuple[float, float]:
    """基于上一交易日收盘价计算涨停价与跌停价。

    交易所口径为四舍五入到分（ROUND_HALF_UP）；Python 内置 round 是
    银行家舍入且受浮点表示影响，边界价会算错（如 10.15×0.9=9.135
    浮点下 round 得 9.13，交易所实际跌停价为 9.14），因此用 Decimal。
    """
    price = Decimal(str(prev_close))
    pct = Decimal(str(_limit_pct(ts_code, is_st)))
    cent = Decimal("0.01")
    limit = (price * (Decimal("1") + pct)).quantize(cent, rounding=ROUND_HALF_UP)
    floor = (price * (Decimal("1") - pct)).quantize(cent, rounding=ROUND_HALF_UP)
    return float(limit), float(floor)


def _is_halted(kline: DailyData, prev_kline: DailyData | None) -> bool:
    """
    判断当日是否停牌。

    heuristic：成交量与成交额均为 0，且开高低收与昨收相同。
    """
    if kline.vol != 0 or kline.amount != 0:
        return False
    if prev_kline is None:
        return True
    return kline.open == prev_kline.close and kline.close == prev_kline.close


def is_price_limit_hit(kline: DailyData, prev_close: float, ts_code: str) -> tuple[bool, str]:
    """
    判断当日是否触发涨停。

    Args:
        kline: 当日 K 线
        prev_close: 上一交易日收盘价
        ts_code: 股票代码，用于判断板块涨跌幅限制

    Returns:
        (是否涨停, 原因说明)
    """
    is_st = _is_st_name(getattr(kline, "name", None))
    limit, _ = _price_limits(prev_close, ts_code, is_st)
    if kline.close >= limit:
        return True, f"涨停（涨停价 {limit:.2f}）"
    return False, ""


def get_trade_constraints(
    ts_code: str,
    kline: DailyData,
    prev_kline: DailyData | None,
    name: str = "",
    allow_st: bool = False,
) -> TradeConstraints:
    """
    判断给定股票在当日的交易约束。

    Args:
        ts_code: 股票代码
        kline: 当日 K 线
        prev_kline: 上一交易日 K 线，用于计算涨跌停价；None 时跳过涨跌停判断
        name: 股票名称，用于 ST 判断
        allow_st: 是否允许交易 ST 股票

    Returns:
        TradeConstraints
    """
    is_st = _is_st_name(name)
    is_halted = _is_halted(kline, prev_kline)

    if is_halted:
        return TradeConstraints(
            can_buy=False,
            can_sell=False,
            reason="停牌",
            is_st=is_st,
            is_halted=True,
        )

    if is_st and not allow_st:
        return TradeConstraints(
            can_buy=False,
            can_sell=True,
            reason="ST 标的默认被过滤",
            is_st=True,
        )

    if prev_kline is None:
        return TradeConstraints(
            can_buy=True,
            can_sell=True,
            reason="无上一日数据，跳过涨跌停判断",
        )

    prev_close = prev_kline.close
    limit, floor = _price_limits(prev_close, ts_code, is_st)

    # 买入：若开盘价 >= 涨停价，视为无法买入
    can_buy = kline.open < limit
    buy_reason = "" if can_buy else f"开盘涨停（涨停价 {limit:.2f}）"

    # 卖出：若收盘价 <= 跌停价，视为当日无法卖出，需顺延
    can_sell = kline.close > floor
    sell_reason = "" if can_sell else f"收盘跌停（跌停价 {floor:.2f}）"

    if not can_buy and not can_sell:
        reason = f"{buy_reason}；{sell_reason}"
    elif not can_buy:
        reason = buy_reason
    elif not can_sell:
        reason = sell_reason
    else:
        reason = "正常交易"

    return TradeConstraints(
        can_buy=can_buy,
        can_sell=can_sell,
        reason=reason,
        price_limit=limit,
        price_floor=floor,
        is_st=is_st,
        is_halted=False,
    )


def next_trading_date(dates: list[str], current: str) -> str:
    """
    返回 current 日期之后的下一个交易日。

    Args:
        dates: 已排序的交易日字符串列表（YYYYMMDD）
        current: 当前日期

    Returns:
        下一交易日；若不存在则返回空字符串
    """
    for d in dates:
        if d > current:
            return d
    return ""
