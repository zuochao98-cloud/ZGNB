#!/usr/bin/env python3
"""
环境权重层。

根据市场环境（强势/震荡/弱势）为不同战法类别分配权重，
支持用户通过 SimulationConfig.strategy_category_weights 覆盖默认值。
"""

from __future__ import annotations

from . import MarketRegime, SimulationConfig


DEFAULT_ENVIRONMENT_WEIGHTS: dict[MarketRegime, dict[str, float]] = {
    MarketRegime.STRONG: {
        "breakout": 1.30,
        "pattern": 1.10,
        "rebound": 0.80,
        "stage": 1.00,
        "risk": 1.20,
    },
    MarketRegime.NEUTRAL: {
        "breakout": 1.00,
        "pattern": 1.00,
        "rebound": 1.00,
        "stage": 1.00,
        "risk": 1.00,
    },
    MarketRegime.WEAK: {
        "breakout": 0.50,
        "pattern": 0.80,
        "rebound": 1.30,
        "stage": 1.00,
        "risk": 1.10,
    },
}


def get_weights(regime: MarketRegime, config: SimulationConfig) -> dict[str, float]:
    """
    获取当前市场环境下各战法类别的权重。

    Args:
        regime: 市场环境
        config: 模拟配置

    Returns:
        category -> weight 的字典
    """
    defaults = DEFAULT_ENVIRONMENT_WEIGHTS.get(regime, DEFAULT_ENVIRONMENT_WEIGHTS[MarketRegime.NEUTRAL]).copy()
    if config.strategy_category_weights:
        defaults.update(config.strategy_category_weights)
    return defaults
