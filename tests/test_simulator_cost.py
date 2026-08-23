"""
模拟器成本模型单元测试
"""

from __future__ import annotations

from modules.indicators import DailyData
from modules.simulator import CostModel, SimulationConfig, SlippageModel
from modules.simulator.cost_model import calculate_costs
from modules.simulator.slippage_model import calculate_slippage


def test_buy_cost_with_min_commission():
    costs = calculate_costs(10000.0, "BUY", CostModel())
    assert costs["commission"] == 5.0
    assert costs["stamp_duty"] == 0.0
    assert costs["total"] == 5.0 + 0.1


def test_sell_cost_includes_stamp_duty():
    costs = calculate_costs(20000.0, "SELL", CostModel())
    assert costs["stamp_duty"] == 20000.0 * 0.0005
    assert costs["total"] == max(20000.0 * 0.00025, 5.0) + costs["stamp_duty"] + 0.2


def test_partial_sell_has_stamp_duty():
    costs = calculate_costs(30000.0, "PARTIAL_SELL", CostModel())
    assert costs["stamp_duty"] == 30000.0 * 0.0005
    assert costs["commission"] == max(30000.0 * 0.00025, 5.0)


def test_stamp_duty_disabled():
    model = CostModel(apply_stamp_duty_on_sell=False)
    costs = calculate_costs(20000.0, "SELL", model)
    assert costs["stamp_duty"] == 0.0
    assert costs["total"] == max(20000.0 * 0.00025, 5.0) + 0.2


def _make_kline(vol: int = 1000) -> DailyData:
    return DailyData(
        ts_code="000001.SZ",
        trade_date="20240101",
        open=10,
        high=12,
        low=9,
        close=10,
        vol=vol,
        amount=10000,
        pct_chg=0,
    )


def test_dynamic_slippage_disabled_uses_config_slippage():
    kline = _make_kline()
    klines = [kline]
    cfg = SimulationConfig(use_dynamic_slippage=False, slippage=0.002)
    assert calculate_slippage(kline, klines, "BUY", cfg) == 0.002


def test_dynamic_slippage_increases_with_atr():
    # 复现 brief 用例：40 根 K 线，相邻 K 线波动相同但为不同对象，确保 ATR 可计算
    klines = [
        DailyData(
            ts_code="000001.SZ",
            trade_date="20240101",
            open=10,
            high=12,
            low=9,
            close=10,
            vol=1000,
            amount=10000,
            pct_chg=0,
        ),
        DailyData(
            ts_code="000001.SZ",
            trade_date="20240102",
            open=10,
            high=12,
            low=9,
            close=10,
            vol=1000,
            amount=10000,
            pct_chg=0,
        ),
    ] * 20
    kline = klines[-1]
    cfg = SimulationConfig(use_dynamic_slippage=True, slippage_model=SlippageModel(base_slippage=0.001))
    s = calculate_slippage(kline, klines, "BUY", cfg)
    assert s > 0.001


def test_dynamic_slippage_adds_volume_penalty():
    base = DailyData(
        ts_code="000001.SZ",
        trade_date="20240101",
        open=10,
        high=12,
        low=9,
        close=10,
        vol=1000,
        amount=10000,
        pct_chg=0,
    )
    # 构造 21 根 K 线，前 20 日成交量相同，最后一日成交量极低
    klines_low = [base] * 20 + [
        DailyData(
            ts_code="000001.SZ",
            trade_date="20240121",
            open=10,
            high=12,
            low=9,
            close=10,
            vol=100,
            amount=1000,
            pct_chg=0,
        )
    ]
    klines_normal = [base] * 21
    kline = klines_low[-1]
    cfg = SimulationConfig(
        use_dynamic_slippage=True,
        slippage_model=SlippageModel(base_slippage=0.001, volume_penalty=0.002),
    )
    s_low = calculate_slippage(kline, klines_low, "BUY", cfg)
    s_normal = calculate_slippage(klines_normal[-1], klines_normal, "BUY", cfg)
    assert s_low > s_normal
    assert round(s_low - s_normal, 6) == 0.002


def test_dynamic_slippage_no_penalty_when_volume_normal():
    base = DailyData(
        ts_code="000001.SZ",
        trade_date="20240101",
        open=10,
        high=12,
        low=9,
        close=10,
        vol=1000,
        amount=10000,
        pct_chg=0,
    )
    klines = [base] * 21
    kline = klines[-1]
    cfg = SimulationConfig(
        use_dynamic_slippage=True,
        slippage_model=SlippageModel(base_slippage=0.001, volume_penalty=0.002),
    )
    s = calculate_slippage(kline, klines, "BUY", cfg)
    # 成交量正常，不触发量惩罚，仅 base + 波动率成分
    assert s == 0.001 + (3.0 / 10.0) * 0.5
