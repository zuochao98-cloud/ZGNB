"""
模拟器仓位管理单元测试
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from modules.indicators import DailyData
from modules.simulator import CostModel, SimulationConfig
from modules.simulator.position_sizer import build_position, calculate_position_size


def _make_klines(
    n: int = 60, ts_code: str = "000001.SZ", start_price: float = 100.0, trend: float = 0.0
) -> list[DailyData]:
    """生成测试 K 线（DailyData 对象）"""
    klines: list[DailyData] = []
    dt = datetime(2024, 1, 1)
    price = start_price
    for i in range(n):
        date_str = dt.strftime("%Y%m%d")
        prev = price
        price *= 1 + trend
        klines.append(
            DailyData(
                ts_code=ts_code,
                trade_date=date_str,
                open=prev,
                high=price * 1.02,
                low=prev * 0.98,
                close=price,
                vol=10000 + i * 100,
                amount=price * (10000 + i * 100),
                pct_chg=trend * 100,
                prev_close=prev,
            )
        )
        dt += timedelta(days=1)
    return klines


def test_basic_size_without_atr():
    shares, risk = calculate_position_size(
        equity=1_000_000,
        entry_price=100.0,
        stop_loss=95.0,
        cash=1_000_000,
        config=SimulationConfig(risk_per_trade=0.02),
    )
    assert shares >= 100
    assert shares % 100 == 0
    assert risk > 0


def test_invalid_stop_loss_returns_zero():
    shares, risk = calculate_position_size(
        equity=1_000_000,
        entry_price=100.0,
        stop_loss=100.0,
        cash=1_000_000,
        config=SimulationConfig(),
    )
    assert shares == 0
    assert risk == 0.0


def test_cash_utilization_limit():
    shares, _ = calculate_position_size(
        equity=1_000_000,
        entry_price=100.0,
        stop_loss=95.0,
        cash=100_000,
        config=SimulationConfig(risk_per_trade=0.02, cash_utilization_limit=0.95),
    )
    # 现金利用率 95%，最多使用 95000 元，每股 100 元，最多 900 股（按 100 取整）
    max_cost = 100_000 * 0.95
    expected = int(max_cost / 100.0 / 100) * 100
    assert shares == expected


def test_max_position_pct_cap():
    entry_price = 100.0
    shares, _ = calculate_position_size(
        equity=1_000_000,
        entry_price=entry_price,
        stop_loss=95.0,
        cash=1_000_000,
        config=SimulationConfig(risk_per_trade=0.02, max_position_pct=0.10),
    )
    # 风险法应得 4000 股，但仓位上限 10% 即 1000 股
    assert shares == 1000
    assert shares * entry_price <= 1_000_000 * 0.10


def test_atr_sizing_increases_risk_per_share():
    klines = _make_klines(n=25, start_price=100.0, trend=0.0)
    # 让最近 20 日窗口内真实波动幅度显著大于固定止损 5 元
    for k in klines[-20:]:
        k.high = 110.0
        k.low = 90.0

    shares_atr, _ = calculate_position_size(
        equity=1_000_000,
        entry_price=100.0,
        stop_loss=95.0,
        cash=1_000_000,
        config=SimulationConfig(
            use_atr_sizing=True,
            atr_window=20,
            risk_per_trade=0.02,
            max_position_pct=1.0,
            cash_utilization_limit=1.0,
        ),
        klines=klines,
    )
    shares_fixed, _ = calculate_position_size(
        equity=1_000_000,
        entry_price=100.0,
        stop_loss=95.0,
        cash=1_000_000,
        config=SimulationConfig(
            use_atr_sizing=False,
            risk_per_trade=0.02,
            max_position_pct=1.0,
            cash_utilization_limit=1.0,
        ),
        klines=klines,
    )
    assert shares_atr < shares_fixed


def test_atr_sizing_ignored_when_klines_insufficient():
    klines = _make_klines(n=5, start_price=100.0, trend=0.0)
    shares, _ = calculate_position_size(
        equity=1_000_000,
        entry_price=100.0,
        stop_loss=95.0,
        cash=1_000_000,
        config=SimulationConfig(
            use_atr_sizing=True,
            atr_window=20,
            risk_per_trade=0.02,
            max_position_pct=1.0,
            cash_utilization_limit=1.0,
        ),
        klines=klines,
    )
    # K 线不足时退化为固定止损
    expected = int((1_000_000 * 0.02) / 5.0 / 100) * 100
    assert shares == expected


def test_atr_sizing_caps_max_position_pct():
    cfg = SimulationConfig(use_atr_sizing=True, max_position_pct=0.10, risk_per_trade=0.02)
    pos = build_position(
        "000001.SZ",
        "测试",
        "20240101",
        100.0,
        95.0,
        110.0,
        cash=1_000_000,
        equity=1_000_000,
        config=cfg,
    )
    assert pos is not None
    assert pos.shares * 100 <= 1_000_000 * 0.10


def test_build_position_sets_extra_fields():
    cfg = SimulationConfig(cost_model=CostModel(commission_rate=0.0003, min_commission=5.0))
    pos = build_position(
        "000001.SZ",
        "平安",
        "20240101",
        100.0,
        95.0,
        110.0,
        cash=1_000_000,
        equity=1_000_000,
        config=cfg,
        can_sell_date="20240102",
        is_st=True,
    )
    assert pos is not None
    assert pos.can_sell_date == "20240102"
    assert pos.is_st is True
    expected_commission = round(pos.shares * 100.0 * 0.0003, 2)
    assert pos.entry_commission == max(expected_commission, 5.0)


def test_build_position_uses_min_commission():
    cfg = SimulationConfig(cost_model=CostModel(commission_rate=0.0003, min_commission=5.0))
    pos = build_position(
        "000001.SZ",
        "平安",
        "20240101",
        10.0,
        9.5,
        11.0,
        cash=100_000,
        equity=100_000,
        config=cfg,
    )
    assert pos is not None
    raw_commission = pos.shares * 10.0 * 0.0003
    if raw_commission < 5.0:
        assert pos.entry_commission == 5.0


def test_build_position_returns_none_when_cash_insufficient():
    pos = build_position(
        "000001.SZ",
        "平安",
        "20240101",
        100.0,
        95.0,
        110.0,
        cash=100.0,
        equity=1_000_000,
        config=SimulationConfig(),
    )
    assert pos is None


def test_build_position_passes_klines_to_sizing():
    klines = _make_klines(n=25, start_price=100.0, trend=0.0)
    klines[-1].high = 120.0
    klines[-1].low = 80.0
    cfg = SimulationConfig(use_atr_sizing=True, atr_window=20, risk_per_trade=0.02)
    pos = build_position(
        "000001.SZ",
        "测试",
        "20240101",
        100.0,
        95.0,
        110.0,
        cash=1_000_000,
        equity=1_000_000,
        config=cfg,
        klines=klines,
    )
    assert pos is not None
    assert pos.shares >= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
