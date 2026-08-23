#!/usr/bin/env python3
"""
参数空间定义与网格生成。

为 walk-forward 参数寻优提供参数维度定义和网格生成功能。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import itertools

from ..constants import (
    BACKTEST_DEFAULT_MAX_POSITION_PCT,
    BACKTEST_HIGH_VOLUME_POSITION_PCT,
    PARAM_STEP_COARSE,
)


@dataclass
class ParamDimension:
    """参数维度定义"""

    name: str  # SimulationConfig 字段名
    param_type: str  # "float" | "int" | "choice"
    low: float | None = None
    high: float | None = None
    step: float | None = None
    choices: list[Any] = field(default_factory=list)

    def generate_values(self) -> list[Any]:
        """生成该维度的所有可能值"""
        if self.param_type == "choice":
            return self.choices.copy()

        if self.low is None or self.high is None or self.step is None:
            raise ValueError(f"维度 {self.name} 缺少 low/high/step")

        values: list[Any] = []
        current = self.low
        while current <= self.high + 1e-9:  # 浮点精度容差
            if self.param_type == "int":
                values.append(int(round(current)))
            else:
                values.append(round(current, 10))  # 避免浮点误差
            current += self.step

        return values


def generate_grid(dimensions: list[ParamDimension]) -> list[dict[str, Any]]:
    """
    生成参数网格（笛卡尔积）。

    Args:
        dimensions: 参数维度列表

    Returns:
        所有参数组合的列表
    """
    if not dimensions:
        return [{}]

    # 生成每个维度的值列表
    value_lists = [dim.generate_values() for dim in dimensions]

    # 计算笛卡尔积
    grid = []
    for combo in itertools.product(*value_lists):
        params = {dim.name: value for dim, value in zip(dimensions, combo)}
        grid.append(params)

    return grid


# 默认参数空间
DEFAULT_PARAM_SPACE: list[ParamDimension] = [
    ParamDimension("min_resonance_score", "float", 0.15, 0.55, 0.10),
    ParamDimension("risk_per_trade", "float", 0.01, 0.03, 0.01),
    ParamDimension("position_score_threshold", "float", 60.0, 80.0, 10.0),
    ParamDimension(
        "max_position_pct",
        "float",
        BACKTEST_DEFAULT_MAX_POSITION_PCT,
        BACKTEST_HIGH_VOLUME_POSITION_PCT,
        PARAM_STEP_COARSE,
    ),
]
