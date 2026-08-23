"""
三波理论测试
"""

from datetime import datetime, timedelta

from modules.indicators import DailyData
from modules.indicators.wave_theory import (
    detect_three_waves,
    classify_wave_for_b1,
    _find_recent_low,
    _count_limit_up,
)


def _make_klines(n, start_price=100.0, daily_pct=0.5, vol_base=10000, limit_up_days=None, noise=0.0):
    """工厂函数：生成 DailyData K线序列"""
    klines = []
    price = start_price
    dt = datetime(2026, 1, 1)
    limit_up_days = set(limit_up_days or [])

    for i in range(n):
        date_str = dt.strftime("%Y%m%d")
        prev_price = price

        # 计算今日涨幅
        if i in limit_up_days:
            pct = 10.0
        else:
            pct = daily_pct + (noise if i % 2 == 0 else -noise)

        price *= 1 + pct / 100
        vol = vol_base * (1 + i * 0.005)

        k = DailyData(
            ts_code="000001.SZ",
            trade_date=date_str,
            open=prev_price * 0.998,
            high=price * 1.01,
            low=prev_price * 0.99,
            close=price,
            vol=vol,
            amount=price * vol,
            pct_chg=pct,
            prev_close=prev_price,
        )
        klines.append(k)
        dt += timedelta(days=1)

    return klines


class TestFindRecentLow:
    def test_find_low_in_uptrend(self):
        klines = _make_klines(60, start_price=100.0, daily_pct=0.5)
        idx, low = _find_recent_low(klines, window=5)
        # 上升趋势中，低点应该在前面
        assert idx < 10
        assert low < 105

    def test_find_low_with_dip(self):
        # 前30天横盘，后30天下跌再反弹
        klines = _make_klines(60, start_price=100.0, daily_pct=0.0)
        # 后20天下跌
        for i in range(40, 60):
            klines[i] = DailyData(
                ts_code="000001.SZ",
                trade_date=klines[i].trade_date,
                open=klines[i].open * 0.98,
                high=klines[i].high * 0.98,
                low=klines[i].low * 0.98,
                close=klines[i].close * 0.98,
                vol=klines[i].vol,
                amount=klines[i].amount,
                pct_chg=-2.0,
                prev_close=klines[i - 1].close if i > 0 else 100.0,
            )
        idx, low = _find_recent_low(klines, window=5)
        # 低点应该在下跌段
        assert idx >= 35


class TestCountLimitUp:
    def test_no_limit_up(self):
        klines = _make_klines(30, daily_pct=2.0)
        assert _count_limit_up(klines, 0) == 0

    def test_with_limit_up(self):
        klines = _make_klines(30, daily_pct=1.0, limit_up_days=[5, 10, 15])
        assert _count_limit_up(klines, 0) == 3


class TestDetectThreeWaves:
    def test_build_wave(self):
        """建仓波：底部起涨 35%，无涨停，连续阳线"""
        klines = _make_klines(60, start_price=100.0, daily_pct=0.6)
        result = detect_three_waves(klines)
        assert result["wave"] == "建仓波"
        assert result["b1_suggestion"] == "可干"
        assert result["confidence"] > 0.5
        assert result["stats"]["gain_pct"] >= 25
        assert result["stats"]["gain_pct"] <= 50

    def test_build_wave_edge_25pct(self):
        """建仓波边界：刚好 25%"""
        klines = _make_klines(50, start_price=100.0, daily_pct=0.45)
        result = detect_three_waves(klines)
        # 25% 涨幅应该在建仓波范围内
        assert result["wave"] in ("建仓波", "拉升波", "未知")

    def test_pull_wave(self):
        """拉升波：快速涨 60%，有涨停"""
        klines = _make_klines(60, start_price=100.0, daily_pct=1.0, limit_up_days=[25, 30])
        result = detect_three_waves(klines)
        assert result["wave"] == "拉升波"
        assert result["b1_suggestion"] == "等回调"

    def test_pull_wave_fast_20day(self):
        """拉升波：快速涨 55%，有 1 次涨停"""
        klines = _make_klines(50, start_price=100.0, daily_pct=0.3)
        # 后 10 天快速拉升 + 1 次涨停
        for i in range(50, 60):
            pct = 10.0 if i == 55 else 3.5
            prev = klines[i - 1].close
            close = prev * (1 + pct / 100)
            klines.append(
                DailyData(
                    ts_code="000001.SZ",
                    trade_date=f"202602{i - 49:02d}",
                    open=prev,
                    high=close * 1.02,
                    low=prev * 0.98,
                    close=close,
                    vol=20000,
                    amount=close * 20000,
                    pct_chg=pct,
                    prev_close=prev,
                )
            )
        result = detect_three_waves(klines)
        assert result["wave"] == "拉升波"

    def test_sprint_wave(self):
        """冲刺波：高位涨 120%，频繁涨停"""
        klines = _make_klines(80, start_price=100.0, daily_pct=1.2, limit_up_days=[30, 35, 40, 45, 50])
        result = detect_three_waves(klines)
        assert result["wave"] == "冲刺波"
        assert result["b1_suggestion"] == "不看"

    def test_unknown_wave_sideways(self):
        """未知：横盘震荡"""
        klines = _make_klines(60, start_price=100.0, daily_pct=0.0, noise=0.5)
        result = detect_three_waves(klines)
        assert result["wave"] == "未知"
        assert result["b1_suggestion"] == "观望"

    def test_insufficient_data(self):
        """数据不足"""
        klines = _make_klines(20)
        result = detect_three_waves(klines)
        assert result["wave"] == "未知"


class TestClassifyWaveForB1:
    def test_build_returns_kegan(self):
        klines = _make_klines(60, start_price=100.0, daily_pct=0.6)
        assert classify_wave_for_b1(klines) == "可干"

    def test_sprint_returns_bukan(self):
        klines = _make_klines(80, start_price=100.0, daily_pct=1.2, limit_up_days=[30, 35, 40])
        assert classify_wave_for_b1(klines) == "不看"
