#!/usr/bin/env python3
"""Walk-forward 参数寻优模块测试"""


def test_walk_forward_config_defaults():
    """测试 WalkForwardConfig 默认值"""
    from modules.simulator.walk_forward import WalkForwardConfig

    config = WalkForwardConfig()

    assert config.train_days == 120
    assert config.test_days == 60
    assert config.objective == "calmar"
    assert config.anchored is False


def test_split_windows_rolling():
    """测试滚动窗口切分"""
    from modules.simulator.walk_forward import _split_windows

    dates = [f"2024010{i}" for i in range(1, 10)]  # 9 天
    windows = _split_windows(dates, train_days=3, test_days=2, anchored=False)

    # 应该有多个窗口
    assert len(windows) > 0

    # 第一个窗口：IS=[0:3], OOS=[3:5]
    is_start, oos_start, oos_end = windows[0]
    assert is_start == 0
    assert oos_start == 3
    assert oos_end == 5


def test_split_windows_anchored():
    """测试锚定窗口切分"""
    from modules.simulator.walk_forward import _split_windows

    dates = [f"2024010{i}" for i in range(1, 10)]  # 9 天
    windows = _split_windows(dates, train_days=3, test_days=2, anchored=True)

    # 所有窗口的 is_start 都应该是 0
    for is_start, oos_start, oos_end in windows:
        assert is_start == 0


def test_evaluate_calmar():
    """测试 Calmar 目标函数"""
    from modules.simulator.walk_forward import _evaluate
    from modules.simulator import SimulationResult, SimulationConfig
    from modules.simulator.metrics import PerformanceMetrics

    config = SimulationConfig()
    metrics = PerformanceMetrics(
        calmar_ratio=2.5,
        sharpe_ratio=1.0,
        sortino_ratio=1.5,
        total_return=0.20,
    )
    result = SimulationResult(config=config, metrics=metrics)

    score = _evaluate(result, "calmar")
    assert score == 2.5


def test_evaluate_all_objectives():
    """测试所有目标函数"""
    from modules.simulator.walk_forward import _evaluate
    from modules.simulator import SimulationResult, SimulationConfig
    from modules.simulator.metrics import PerformanceMetrics

    config = SimulationConfig()
    metrics = PerformanceMetrics(
        calmar_ratio=2.5,
        sharpe_ratio=1.0,
        sortino_ratio=1.5,
        total_return=0.20,
    )
    result = SimulationResult(config=config, metrics=metrics)

    assert _evaluate(result, "calmar") == 2.5
    assert _evaluate(result, "sharpe") == 1.0
    assert _evaluate(result, "sortino") == 1.5
    assert _evaluate(result, "total_return") == 0.20
    assert _evaluate(result, "unknown") == 0.0


def test_evaluate_no_metrics():
    """测试无指标时的默认得分"""
    from modules.simulator.walk_forward import _evaluate
    from modules.simulator import SimulationResult, SimulationConfig

    result = SimulationResult(config=SimulationConfig(), metrics=None)
    assert _evaluate(result, "calmar") == 0.0


def test_split_windows_insufficient_data():
    """测试数据不足时返回空窗口列表"""
    from modules.simulator.walk_forward import _split_windows

    # 只有 4 天，不够 train=3 + test=2 = 5
    dates = [f"2024010{i}" for i in range(1, 5)]
    windows = _split_windows(dates, train_days=3, test_days=2, anchored=False)
    assert len(windows) == 0


def test_run_walk_forward_with_mock():
    """使用 mock 测试 walk-forward 编排逻辑（不依赖真实数据）"""
    from unittest.mock import patch, MagicMock
    from modules.simulator.walk_forward import run_walk_forward, WalkForwardConfig
    from modules.simulator import SimulationConfig, SimulationResult
    from modules.simulator.param_space import ParamDimension
    from modules.simulator.metrics import PerformanceMetrics

    # 构造模拟的 SimulationResult
    call_count = 0

    def fake_run_simulation(ts_codes, days, config, datasource, start_date=None, end_date=None):
        nonlocal call_count
        call_count += 1
        # 交替返回不同指标，模拟参数搜索效果
        calmar = 1.0 + (call_count % 3) * 0.5
        metrics = PerformanceMetrics(calmar_ratio=calmar, sharpe_ratio=calmar * 0.5)
        return SimulationResult(
            config=config,
            equity_curve=[1000000 + call_count * 1000 for i in range(1, days + 1)],
            equity_details=[{"date": f"2024010{i}", "equity": 1000000 + call_count * 1000} for i in range(1, days + 1)],
            metrics=metrics,
        )

    # 构造日期序列
    fake_dates = [f"202401{i:02d}" for i in range(1, 10)]

    base_config = SimulationConfig(initial_capital=1_000_000)
    wf_config = WalkForwardConfig(
        train_days=3,
        test_days=2,
        objective="calmar",
        param_space=[ParamDimension("risk_per_trade", "float", 0.01, 0.02, 0.01)],
    )

    with patch("modules.simulator.walk_forward.run_simulation", side_effect=fake_run_simulation):
        with patch("modules.simulator.walk_forward._available_dates", return_value=fake_dates):
            result = run_walk_forward(
                ts_codes=["000001.SZ"],
                total_days=9,
                wf_config=wf_config,
                base_config=base_config,
                datasource=MagicMock(),
            )

    # 验证结果结构
    assert result is not None
    assert len(result.windows) > 0
    assert result.oos_metrics is not None
    assert result.overfit_ratio > 0

    # 验证每个窗口有最佳参数
    for w in result.windows:
        assert "risk_per_trade" in w.best_params
        assert w.is_score > 0

    # 验证 OOS 资金曲线已拼接
    assert len(result.oos_equity_curve) > 0


def test_run_walk_forward_insufficient_data():
    """测试数据不足时返回空结果"""
    from unittest.mock import patch, MagicMock
    from modules.simulator.walk_forward import run_walk_forward, WalkForwardConfig
    from modules.simulator import SimulationConfig
    from modules.simulator.param_space import ParamDimension

    base_config = SimulationConfig()
    wf_config = WalkForwardConfig(
        train_days=60,
        test_days=30,
        param_space=[ParamDimension("risk_per_trade", "float", 0.02, 0.02, 0.01)],
    )

    # 只返回 10 天数据，不够 60+30=90
    with patch("modules.simulator.walk_forward._available_dates", return_value=[f"2024010{i}" for i in range(1, 11)]):
        result = run_walk_forward(
            ts_codes=["000001.SZ"],
            total_days=10,
            wf_config=wf_config,
            base_config=base_config,
            datasource=MagicMock(),
        )

    assert result.windows == []
    assert result.overfit_ratio == 1.0
