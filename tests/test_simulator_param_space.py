#!/usr/bin/env python3
"""参数空间模块测试"""


def test_param_dimension_creation():
    """测试参数维度创建"""
    from modules.simulator.param_space import ParamDimension

    dim = ParamDimension(
        name="risk_per_trade",
        param_type="float",
        low=0.01,
        high=0.03,
        step=0.01,
    )

    assert dim.name == "risk_per_trade"
    assert dim.param_type == "float"
    assert dim.low == 0.01
    assert dim.high == 0.03
    assert dim.step == 0.01


def test_generate_grid_single_dimension():
    """测试单维度网格生成"""
    from modules.simulator.param_space import ParamDimension, generate_grid

    dim = ParamDimension("risk", "float", 0.01, 0.03, 0.01)
    grid = generate_grid([dim])

    assert len(grid) == 3
    assert grid[0] == {"risk": 0.01}
    assert grid[1] == {"risk": 0.02}
    assert grid[2] == {"risk": 0.03}


def test_generate_grid_multiple_dimensions():
    """测试多维度网格生成（笛卡尔积）"""
    from modules.simulator.param_space import ParamDimension, generate_grid

    dim1 = ParamDimension("a", "float", 1.0, 2.0, 1.0)
    dim2 = ParamDimension("b", "int", 10, 20, 10)

    grid = generate_grid([dim1, dim2])

    assert len(grid) == 4  # 2 × 2
    assert {"a": 1.0, "b": 10} in grid
    assert {"a": 1.0, "b": 20} in grid
    assert {"a": 2.0, "b": 10} in grid
    assert {"a": 2.0, "b": 20} in grid


def test_generate_grid_with_choices():
    """测试使用 choices 的网格生成"""
    from modules.simulator.param_space import ParamDimension, generate_grid

    dim = ParamDimension("mode", "choice", choices=["simple", "resonance"])
    grid = generate_grid([dim])

    assert len(grid) == 2
    assert {"mode": "simple"} in grid
    assert {"mode": "resonance"} in grid
