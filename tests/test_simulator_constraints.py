#!/usr/bin/env python3
"""交易约束层单元测试。"""

from modules.indicators import DailyData
from modules.simulator import Position, SimulationConfig
from modules.simulator.execution_constraints import (
    TradeConstraints,
    get_trade_constraints,
    is_price_limit_hit,
    next_trading_date,
)
from modules.simulator.exit_manager import check_exit


def test_main_board_price_limit():
    prev = DailyData(
        ts_code="000001.SZ",
        trade_date="20240101",
        open=10,
        high=11,
        low=9,
        close=10,
        vol=1000,
        amount=10000,
        pct_chg=0,
    )
    kline = DailyData(
        ts_code="000001.SZ",
        trade_date="20240102",
        open=11.1,
        high=11.1,
        low=11.0,
        close=11.0,
        vol=1000,
        amount=10000,
        pct_chg=10,
    )
    c = get_trade_constraints("000001.SZ", kline, prev)
    assert c.can_buy is False
    assert "涨停" in c.reason


def test_main_board_price_limits_use_half_up_rounding():
    prev = DailyData(
        ts_code="000001.SZ",
        trade_date="20240101",
        open=10.15,
        high=10.15,
        low=10.15,
        close=10.15,
        vol=1000,
        amount=10150,
        pct_chg=0,
    )
    kline = DailyData(
        ts_code="000001.SZ",
        trade_date="20240102",
        open=10.15,
        high=10.20,
        low=10.10,
        close=10.15,
        vol=1000,
        amount=10150,
        pct_chg=0,
    )

    constraints = get_trade_constraints("000001.SZ", kline, prev)

    # 10.15 × 0.9 = 9.135 → 交易所四舍五入到分 = 9.14；
    # 浮点 round 会得 9.13（银行家舍入 + 浮点表示 9.134999...）。
    assert constraints.price_floor == 9.14
    assert constraints.price_limit == 11.17


def test_kcb_20pct_limit():
    prev = DailyData(
        ts_code="688001.SH",
        trade_date="20240101",
        open=10,
        high=11,
        low=9,
        close=10,
        vol=1000,
        amount=10000,
        pct_chg=0,
    )
    kline = DailyData(
        ts_code="688001.SH",
        trade_date="20240102",
        open=12.1,
        high=12.1,
        low=12.0,
        close=12.0,
        vol=1000,
        amount=10000,
        pct_chg=20,
    )
    c = get_trade_constraints("688001.SH", kline, prev)
    assert c.can_buy is False


def test_st_filter_and_5pct():
    prev = DailyData(
        ts_code="000002.SZ",
        trade_date="20240101",
        open=5,
        high=5.5,
        low=4.5,
        close=5,
        vol=1000,
        amount=10000,
        pct_chg=0,
    )
    kline = DailyData(
        ts_code="000002.SZ",
        trade_date="20240102",
        open=5.26,
        high=5.26,
        low=5.25,
        close=5.25,
        vol=1000,
        amount=10000,
        pct_chg=5,
    )
    c = get_trade_constraints("000002.SZ", kline, prev, name="*ST 测试", allow_st=False)
    assert c.is_st is True
    assert c.can_buy is False


def test_halted_stock():
    prev = DailyData(
        ts_code="000003.SZ",
        trade_date="20240101",
        open=10,
        high=10,
        low=10,
        close=10,
        vol=1000,
        amount=10000,
        pct_chg=0,
    )
    kline = DailyData(
        ts_code="000003.SZ",
        trade_date="20240102",
        open=10,
        high=10,
        low=10,
        close=10,
        vol=0,
        amount=0,
        pct_chg=0,
    )
    c = get_trade_constraints("000003.SZ", kline, prev)
    assert c.is_halted is True
    assert c.can_sell is False


def test_trade_constraints_dataclass_defaults():
    c = TradeConstraints(can_buy=True, can_sell=True, reason="正常交易")
    assert c.price_limit is None
    assert c.price_floor is None
    assert c.is_st is False
    assert c.is_halted is False


def test_next_trading_date_basic():
    dates = ["20240101", "20240102", "20240103"]
    assert next_trading_date(dates, "20240101") == "20240102"
    assert next_trading_date(dates, "20240102") == "20240103"
    assert next_trading_date(dates, "20240103") == ""


def test_is_price_limit_hit_main_board():
    kline = DailyData(
        ts_code="000001.SZ",
        trade_date="20240102",
        open=11.0,
        high=11.1,
        low=11.0,
        close=11.0,
        vol=1000,
        amount=10000,
        pct_chg=10,
    )
    hit, reason = is_price_limit_hit(kline, prev_close=10.0, ts_code="000001.SZ")
    assert hit is True
    assert "涨停" in reason


def test_is_price_limit_hit_kcb_20pct():
    kline = DailyData(
        ts_code="688001.SH",
        trade_date="20240102",
        open=12.0,
        high=12.1,
        low=12.0,
        close=12.0,
        vol=1000,
        amount=10000,
        pct_chg=20,
    )
    hit, reason = is_price_limit_hit(kline, prev_close=10.0, ts_code="688001.SH")
    assert hit is True
    assert "12.00" in reason


def test_t1_blocks_sell_on_entry_date():
    """T+1 锁定：当前日期早于 can_sell_date 时，即使触发止损也不得卖出。"""
    pos = Position(
        ts_code="000001.SZ",
        name="测试",
        entry_date="20240101",
        entry_price=100,
        shares=100,
        stop_loss=95,
        take_profit=110,
        risk_amount=1000,
        can_sell_date="20240102",
    )
    klines = [
        DailyData(
            ts_code="000001.SZ",
            trade_date="20240101",
            open=100,
            high=100,
            low=94,
            close=94,
            vol=100,
            amount=1000,
            pct_chg=-6,
        )
    ]
    action, shares = check_exit(pos, klines, SimulationConfig(t1_lock=True))
    assert action == "HOLD"
    assert shares == 0
    assert any("T+1锁定" in note for note in pos.notes)


def test_t1_allows_sell_on_can_sell_date():
    """T+1 锁定：当前日期等于 can_sell_date 时，允许正常卖出。"""
    pos = Position(
        ts_code="000001.SZ",
        name="测试",
        entry_date="20240101",
        entry_price=100,
        shares=100,
        stop_loss=95,
        take_profit=110,
        risk_amount=1000,
        can_sell_date="20240102",
    )
    klines = [
        DailyData(
            ts_code="000001.SZ",
            trade_date="20240102",
            open=100,
            high=100,
            low=94,
            close=94,
            vol=100,
            amount=1000,
            pct_chg=-6,
        )
    ]
    action, shares = check_exit(pos, klines, SimulationConfig(t1_lock=True))
    assert action == "STOP_LOSS"
    assert shares == 100


def test_limit_down_blocks_sell():
    """跌停约束阻止卖出：交易约束 can_sell=False 时强制 HOLD。"""
    pos = Position(
        ts_code="000001.SZ",
        name="测试",
        entry_date="20240101",
        entry_price=100,
        shares=100,
        stop_loss=95,
        take_profit=110,
        risk_amount=1000,
        can_sell_date="20240101",
    )
    klines = [
        DailyData(
            ts_code="000001.SZ",
            trade_date="20240101",
            open=100,
            high=100,
            low=94,
            close=94,
            vol=100,
            amount=1000,
            pct_chg=-6,
        )
    ]
    constraints = TradeConstraints(can_buy=True, can_sell=False, reason="收盘跌停")
    action, shares = check_exit(pos, klines, SimulationConfig(t1_lock=False), constraints=constraints)
    assert action == "HOLD"
    assert shares == 0
    assert any("跌停" in note or "交易约束阻止卖出" in note for note in pos.notes)


def test_normal_stop_loss_after_t1():
    """T+1 解禁后，正常止损逻辑仍然生效。"""
    pos = Position(
        ts_code="000001.SZ",
        name="测试",
        entry_date="20240101",
        entry_price=100,
        shares=100,
        stop_loss=95,
        take_profit=110,
        risk_amount=1000,
        can_sell_date="20240102",
    )
    klines = [
        DailyData(
            ts_code="000001.SZ",
            trade_date="20240103",
            open=100,
            high=100,
            low=94,
            close=94,
            vol=100,
            amount=1000,
            pct_chg=-6,
        )
    ]
    action, shares = check_exit(pos, klines, SimulationConfig(t1_lock=True))
    assert action == "STOP_LOSS"
    assert shares == 100
    assert not any("T+1锁定" in note for note in pos.notes)
