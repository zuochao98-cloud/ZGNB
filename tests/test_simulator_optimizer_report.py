#!/usr/bin/env python3
"""optimizer_report 模块测试。"""

from __future__ import annotations


def test_summary_text_format():
    """测试文本报告格式"""
    from modules.simulator.optimizer_report import summary_text
    from modules.simulator.walk_forward import WalkForwardResult, WalkForwardConfig, WalkForwardWindow
    from modules.simulator import SimulationResult, SimulationConfig
    from modules.simulator.metrics import PerformanceMetrics

    config = WalkForwardConfig(train_days=120, test_days=60, objective="calmar")
    metrics = PerformanceMetrics(
        annualized_return=0.25,
        sharpe_ratio=1.5,
        calmar_ratio=2.0,
        max_drawdown=0.15,
        win_rate=0.55,
    )

    window = WalkForwardWindow(
        window_index=0,
        is_start="20240101",
        is_end="20240430",
        oos_start="20240501",
        oos_end="20240630",
        best_params={"risk_per_trade": 0.02},
        is_score=2.5,
        oos_score=1.8,
        is_result=SimulationResult(config=SimulationConfig()),
        oos_result=SimulationResult(config=SimulationConfig()),
    )

    result = WalkForwardResult(
        config=config,
        windows=[window],
        oos_equity_curve=[],
        oos_metrics=metrics,
        overfit_ratio=1.39,
    )

    text = summary_text(result)

    assert "Walk-forward 参数寻优结果" in text
    assert "窗口数:       1" in text
    assert "训练天数:     120" in text
    assert "验证天数:     60" in text
    assert "目标函数:     calmar" in text
    assert "过拟合比率:   1.39" in text
    assert "年化收益:   +25.00%" in text
    assert "夏普比率:   1.50" in text
    assert "窗口 0: IS=2.50, OOS=1.80" in text
    assert "risk_per_trade = 0.02" in text


def test_to_dict_structure():
    """测试 JSON 输出结构"""
    from modules.simulator.optimizer_report import to_dict
    from modules.simulator.walk_forward import WalkForwardResult, WalkForwardConfig, WalkForwardWindow
    from modules.simulator import SimulationResult, SimulationConfig
    from modules.simulator.metrics import PerformanceMetrics

    config = WalkForwardConfig()
    metrics = PerformanceMetrics()

    result = WalkForwardResult(
        config=config,
        windows=[],
        oos_equity_curve=[{"date": "20240101", "equity": 1000000}],
        oos_metrics=metrics,
        overfit_ratio=1.0,
    )

    data = to_dict(result)

    assert "config" in data
    assert "windows" in data
    assert "oos_equity_curve" in data
    assert "oos_metrics" in data
    assert "overfit_ratio" in data
