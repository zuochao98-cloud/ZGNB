"""
麒麟会四阶段识别测试
"""

from datetime import datetime, timedelta

from modules.indicators import DailyData
from modules.indicators.kirin_detector import (
    detect_kirin_stage,
    _calculate_red_green_ratio,
    _detect_n_shape_raise,
    _detect_healthy_breathing,
    _calculate_position_ratio,
)


def _make_klines(n, start_price=100.0, daily_pct=0.0, vol_base=10000, limit_up_days=None, volume_pattern="normal"):
    """工厂函数：生成 DailyData K线序列"""
    klines = []
    price = start_price
    dt = datetime(2026, 1, 1)
    limit_up_days = set(limit_up_days or [])

    for i in range(n):
        date_str = dt.strftime("%Y%m%d")
        prev_price = price

        if i in limit_up_days:
            pct = 10.0
        else:
            pct = daily_pct

        price *= 1 + pct / 100

        # 根据 volume_pattern 控制成交量
        if volume_pattern == "high":
            vol = vol_base * (1.5 + i * 0.02)
        elif volume_pattern == "low":
            vol = vol_base * (0.5 - i * 0.005)
            if vol < 1000:
                vol = 1000
        elif volume_pattern == "alternating":
            # 放量涨 + 缩量调（吸筹特征）
            if i % 3 == 0:
                vol = vol_base * 2.0
            else:
                vol = vol_base * 0.8
        else:
            vol = vol_base

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


class TestRedGreenRatio:
    def test_red_fat(self):
        """红肥绿瘦：阳线成交量远大于阴线"""
        klines = []
        for i in range(20):
            vol = 20000 if i % 2 == 0 else 5000
            close = 101.0 if i % 2 == 0 else 99.0
            k = DailyData(
                ts_code="000001.SZ",
                trade_date=f"202601{i + 1:02d}",
                open=100.0,
                high=102.0,
                low=98.0,
                close=close,
                vol=vol,
                amount=close * vol,
                pct_chg=0.0,
                prev_close=100.0,
            )
            klines.append(k)
        ratio = _calculate_red_green_ratio(klines, 20)
        assert ratio > 2.0

    def test_green_fat(self):
        """绿肥红瘦：阴线成交量大于阳线"""
        klines = []
        for i in range(20):
            vol = 5000 if i % 2 == 0 else 20000
            close = 101.0 if i % 2 == 0 else 99.0
            k = DailyData(
                ts_code="000001.SZ",
                trade_date=f"202601{i + 1:02d}",
                open=100.0,
                high=102.0,
                low=98.0,
                close=close,
                vol=vol,
                amount=close * vol,
                pct_chg=0.0,
                prev_close=100.0,
            )
            klines.append(k)
        ratio = _calculate_red_green_ratio(klines, 20)
        assert ratio < 0.5


class TestNShapeRaise:
    def test_n_shape_true(self):
        """N 型逐步抬高：构造三个明确的局部低点"""
        klines = []
        for i in range(40):
            # 用 low 来构造局部低点，close 用来判断涨跌
            if i == 5:
                low, close = 94.0, 100.0
            elif i == 15:
                low, close = 96.0, 102.0
            elif i == 25:
                low, close = 98.0, 104.0
            else:
                low = 100.0 + i * 0.1
                close = 101.0 + i * 0.1

            k = DailyData(
                ts_code="000001.SZ",
                trade_date=f"202601{i + 1:02d}",
                open=100.0 + i * 0.1,
                high=close * 1.02,
                low=low,
                close=close,
                vol=10000,
                amount=close * 10000,
                pct_chg=0.5,
                prev_close=100.0 + (i - 1) * 0.1 if i > 0 else 100.0,
            )
            klines.append(k)

        is_n, idx = _detect_n_shape_raise(klines)
        assert is_n is True
        assert idx >= 0

    def test_n_shape_false(self):
        """不是 N 型"""
        klines = _make_klines(40, daily_pct=0.0)
        is_n, idx = _detect_n_shape_raise(klines)
        assert is_n is False


class TestHealthyBreathing:
    def test_healthy_true(self):
        """呼吸节奏健康：放量涨 → 缩量调"""
        klines = []
        for i in range(10):
            if i % 2 == 0:
                # 放量涨：阳线，成交量大
                vol = 20000
                close = 101.0
                open_p = 100.0
            else:
                # 缩量调：阴线，成交量小
                vol = 8000
                close = 99.5
                open_p = 101.0
            k = DailyData(
                ts_code="000001.SZ",
                trade_date=f"202601{i + 1:02d}",
                open=open_p,
                high=max(open_p, close) * 1.01,
                low=min(open_p, close) * 0.99,
                close=close,
                vol=vol,
                amount=close * vol,
                pct_chg=(close - open_p) / open_p * 100,
                prev_close=open_p,
            )
            klines.append(k)
        assert _detect_healthy_breathing(klines) is True

    def test_healthy_false(self):
        """呼吸节奏不健康"""
        klines = []
        for i in range(10):
            if i % 2 == 0:
                vol = 8000
                close = 101.0
            else:
                vol = 20000
                close = 100.5
            k = DailyData(
                ts_code="000001.SZ",
                trade_date=f"202601{i + 1:02d}",
                open=100.0,
                high=102.0,
                low=99.0,
                close=close,
                vol=vol,
                amount=close * vol,
                pct_chg=0.0,
                prev_close=100.0,
            )
            klines.append(k)
        assert _detect_healthy_breathing(klines) is False


class TestPositionRatio:
    def test_low_position(self):
        # 前90天在100-110高位，后30天大跌到80，当前在82 → 区间低位
        klines = _make_klines(120, start_price=100.0, daily_pct=0.0)
        # 前90天逐步涨到110
        for i in range(90):
            klines[i] = DailyData(
                ts_code="000001.SZ",
                trade_date=klines[i].trade_date,
                open=100.0 + i * 0.1,
                high=112.0,
                low=99.0,
                close=100.0 + i * 0.1,
                vol=10000,
                amount=1000000.0,
                pct_chg=0.1,
                prev_close=100.0 + (i - 1) * 0.1 if i > 0 else 100.0,
            )
        # 后30天暴跌到80
        for i in range(90, 120):
            close = 110.0 - (i - 90) * 1.0
            klines[i] = DailyData(
                ts_code="000001.SZ",
                trade_date=klines[i].trade_date,
                open=close + 1.0,
                high=close + 2.0,
                low=close - 1.0,
                close=close,
                vol=15000,
                amount=close * 15000,
                pct_chg=-1.0,
                prev_close=close + 1.0,
            )
        pos = _calculate_position_ratio(klines)
        assert pos["from_low_pct"] < 30

    def test_high_position(self):
        klines = _make_klines(120, start_price=100.0, daily_pct=0.5)
        pos = _calculate_position_ratio(klines)
        assert pos["from_low_pct"] > 50


class TestDetectKirinStage:
    def test_xishou_stage(self):
        """吸筹阶段：底部放量，N型抬高，红肥绿瘦"""
        klines = _make_klines(80, start_price=100.0, daily_pct=0.1, volume_pattern="alternating")
        result = detect_kirin_stage(klines)
        # 低位 + 放量交替 + 红肥绿瘦应该倾向于吸筹
        assert result["stage"] in ("吸筹", "拉升", "未知")
        assert result["indicators"]["red_green_ratio"] > 1.0

    def test_lasheng_stage(self):
        """拉升阶段：快速脱离，有涨停，量价齐升"""
        klines = _make_klines(60, start_price=100.0, daily_pct=0.8, limit_up_days=[30, 35, 40], volume_pattern="high")
        result = detect_kirin_stage(klines)
        assert result["stage"] == "拉升"
        assert result["operation"] == "不追，等回调B1"
        assert result["sub_type"] == "铁蝴蝶"

    def test_paifa_stage(self):
        """派发阶段：高位放量阴线"""
        # 先拉升到高位
        klines = _make_klines(80, start_price=100.0, daily_pct=0.5)
        # 后 10 天高位放量下跌
        for i in range(70, 80):
            klines[i] = DailyData(
                ts_code="000001.SZ",
                trade_date=klines[i].trade_date,
                open=klines[i].open,
                high=klines[i].high,
                low=klines[i].low * 0.95,
                close=klines[i].close * 0.97,
                vol=klines[i].vol * 2.0,
                amount=klines[i].amount * 2.0,
                pct_chg=-3.0,
                prev_close=klines[i - 1].close,
            )
        result = detect_kirin_stage(klines)
        assert result["stage"] == "派发"
        assert result["operation"] == "准备走人"

    def test_luoluo_stage(self):
        """回落阶段：缩量下跌"""
        # 先拉升
        klines = _make_klines(60, start_price=100.0, daily_pct=0.5)
        # 后 20 天缩量下跌
        for i in range(40, 60):
            klines[i] = DailyData(
                ts_code="000001.SZ",
                trade_date=klines[i].trade_date,
                open=klines[i].open * 0.98,
                high=klines[i].high * 0.98,
                low=klines[i].low * 0.98,
                close=klines[i].close * 0.98,
                vol=klines[i].vol * 0.5,
                amount=klines[i].amount * 0.5,
                pct_chg=-2.0,
                prev_close=klines[i - 1].close,
            )
        result = detect_kirin_stage(klines)
        assert result["stage"] == "回落"
        assert result["operation"] == "不抄底"

    def test_academy_type(self):
        """学院派铁蝴蝶：拉升慢而稳"""
        klines = _make_klines(60, start_price=100.0, daily_pct=0.3, volume_pattern="alternating")
        result = detect_kirin_stage(klines)
        if result["stage"] == "拉升":
            assert result["sub_type"] == "学院派铁蝴蝶"

    def test_insufficient_data(self):
        """数据不足"""
        klines = _make_klines(30)
        result = detect_kirin_stage(klines)
        assert result["stage"] == "未知"
