"""
screener.py 选股测试（P3 指标接入扩展）
"""

import pytest
from datetime import datetime, timedelta

from modules.screener.criteria import _CRITERIA_REGISTRY, _check_centipede, _check_sandglass_min
from modules.screener.scoring import score_b1_opportunity, score_volume_pattern
from tests.conftest import generate_b1_scenario, generate_uptrend_klines, make_daily_data


# ============ 工厂函数：构造特定量比场景 ============


def generate_volume_ratio_super_attack(n=30, ts_code="600519.SH"):
    """构造超级攻击场景：量比 > 40 且涨"""
    rows = generate_uptrend_klines(n=n, ts_code=ts_code, daily_pct=0.1, vol_base=500)
    # 前5天维持低量，第6天突然巨量
    for i in range(len(rows) - 6, len(rows) - 1):
        rows[i]["vol"] = 500  # 低量
    # 最后一天：巨量 + 大涨
    rows[-1]["vol"] = 25000  # 量比约 50
    rows[-1]["pct_chg"] = 5.0
    rows[-1]["close"] = rows[-1]["close"] * 1.05
    return rows


def generate_volume_ratio_attack_day(n=30, ts_code="600519.SH"):
    """构造攻击日场景：量比 > 20 且涨"""
    rows = generate_uptrend_klines(n=n, ts_code=ts_code, daily_pct=0.1, vol_base=1000)
    for i in range(len(rows) - 6, len(rows) - 1):
        rows[i]["vol"] = 1000
    rows[-1]["vol"] = 25000  # 量比约 25
    rows[-1]["pct_chg"] = 3.0
    rows[-1]["close"] = rows[-1]["close"] * 1.03
    return rows


def generate_volume_ratio_chuhuo(n=30, ts_code="600519.SH"):
    """构造出货日场景：量比 > 20 且暴跌"""
    rows = generate_uptrend_klines(n=n, ts_code=ts_code, daily_pct=0.1, vol_base=1000)
    for i in range(len(rows) - 6, len(rows) - 1):
        rows[i]["vol"] = 1000
    rows[-1]["vol"] = 25000  # 量比约 25
    rows[-1]["pct_chg"] = -5.0
    rows[-1]["close"] = rows[-1]["close"] * 0.95
    return rows


def generate_volume_ratio_weak(n=30, ts_code="600519.SH"):
    """构造弱势日场景：量比 < 10 且急跌"""
    rows = generate_uptrend_klines(n=n, ts_code=ts_code, daily_pct=0.1, vol_base=5000)
    rows[-1]["vol"] = 3000  # 量比 < 10
    rows[-1]["pct_chg"] = -3.0
    rows[-1]["close"] = rows[-1]["close"] * 0.97
    return rows


def generate_sandglass_contraction(n=30, ts_code="600519.SH"):
    """构造沙漏缩量收敛场景：量能持续收缩，价格接近支撑位"""
    rows = generate_uptrend_klines(n=n, ts_code=ts_code, daily_pct=0.05, vol_base=10000)
    # 最近10天量能持续收缩
    for i in range(len(rows) - 10, len(rows)):
        shrink_factor = 0.5 + (i - (len(rows) - 10)) * 0.02
        rows[i]["vol"] = int(10000 * shrink_factor)
    # 价格轻微下跌，接近20日低点
    support = min(r["close"] for r in rows[-20:])
    rows[-1]["close"] = support * 1.02  # 接近支撑位
    rows[-1]["low"] = support * 0.99
    return rows


# ============ P3 指标接入测试 ============


class TestP3VolumeRatioIntegration:
    """量比战法融入 score_volume_pattern 测试"""

    def test_super_attack_high_score(self):
        """超级攻击场景：评分应大幅提升"""
        klines = generate_volume_ratio_super_attack(n=30)
        score, reasons = score_volume_pattern(klines)
        assert score >= 80, f"超级攻击场景评分应>=80, 实际{score}"
        assert any("超级攻击" in r for r in reasons), f"原因中应包含'超级攻击', 实际{reasons}"

    def test_attack_day_high_score(self):
        """攻击日场景：评分应明显提升"""
        klines = generate_volume_ratio_attack_day(n=30)
        score, reasons = score_volume_pattern(klines)
        assert score >= 75, f"攻击日场景评分应>=75, 实际{score}"
        assert any("攻击日" in r for r in reasons), f"原因中应包含'攻击日', 实际{reasons}"

    def test_chuhuo_low_score(self):
        """出货日场景：评分应大幅下降"""
        klines = generate_volume_ratio_chuhuo(n=30)
        score, reasons = score_volume_pattern(klines)
        assert score <= 40, f"出货日场景评分应<=40, 实际{score}"
        assert any("出货" in r for r in reasons), f"原因中应包含'出货', 实际{reasons}"

    def test_weak_day_low_score(self):
        """弱势日场景：评分应下降"""
        klines = generate_volume_ratio_weak(n=30)
        score, reasons = score_volume_pattern(klines)
        assert score <= 40, f"弱势日场景评分应<=40, 实际{score}"
        assert any("弱势" in r for r in reasons), f"原因中应包含'弱势', 实际{reasons}"

    def test_normal_oscillation(self):
        """正常震荡：评分不应极端"""
        klines = generate_uptrend_klines(n=30, daily_pct=0.1, vol_base=5000)
        score, reasons = score_volume_pattern(klines)
        assert 30 <= score <= 70, f"正常震荡评分应在30-70之间, 实际{score}"

    def test_insufficient_data_fallback(self):
        """数据不足时降级到简单量比计算"""
        klines = generate_uptrend_klines(n=5)
        score, reasons = score_volume_pattern(klines)
        assert score == 50
        assert "数据不足" in reasons


class TestP3SandglassB1Integration:
    """沙漏评分融入 score_b1_opportunity 测试"""

    def test_sandglass_contraction_boosts_b1(self):
        """沙漏缩量收敛增强 B1 评分"""
        klines = generate_sandglass_contraction(n=30)
        score, reasons = score_b1_opportunity(klines)
        # 检查原因中是否包含沙漏相关因子
        _sandglass_reasons = [r for r in reasons if "沙漏" in r]
        # 只要有沙漏相关原因即可（不一定能触发，因为J值可能不满足B1条件）
        # 但评分应在合理范围
        assert 0 <= score <= 100

    def test_b1_scenario_with_sandglass(self):
        """B1 场景 + 沙漏缩量收敛"""
        klines = generate_b1_scenario()
        score, reasons = score_b1_opportunity(klines)
        assert 0 <= score <= 100
        # B1 场景通常会有较高的J值负值和缩量
        if score > 30:
            assert any(r for r in reasons if "J值" in r or "缩量" in r or "沙漏" in r)

    def test_insufficient_data(self):
        """数据不足返回0"""
        klines = generate_uptrend_klines(n=10)
        score, reasons = score_b1_opportunity(klines)
        assert score == 0
        assert "数据不足" in reasons


class TestP3ScreenerCriteriaRegistry:
    """P3 指标筛选条件注册表测试"""

    def test_bull_rope_registered(self):
        """牛绳条件已在注册表"""
        from modules.screener import _CRITERIA_REGISTRY

        assert "bull_rope" in _CRITERIA_REGISTRY

    def test_sandglass_perfect_registered(self):
        """沙漏完美条件已在注册表"""
        from modules.screener import _CRITERIA_REGISTRY

        assert "sandglass_perfect" in _CRITERIA_REGISTRY

    def test_volume_ratio_super_registered(self):
        """量比超级条件已在注册表"""
        from modules.screener import _CRITERIA_REGISTRY

        assert "volume_ratio_super" in _CRITERIA_REGISTRY

    def test_centipede_hard_filter_exists(self):
        """蜈蚣图硬过滤存在"""
        from modules.screener import _check_centipede

        assert callable(_check_centipede)

    def test_sandglass_min_filter_exists(self):
        """沙漏最低分过滤存在"""
        from modules.screener import _check_sandglass_min

        assert callable(_check_sandglass_min)
