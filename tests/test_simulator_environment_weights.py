#!/usr/bin/env python3
"""环境权重层单元测试。"""

from __future__ import annotations

from modules.simulator.environment_weights import get_weights, DEFAULT_ENVIRONMENT_WEIGHTS
from modules.simulator import SimulationConfig, MarketRegime


def test_default_weights_for_strong():
    weights = get_weights(MarketRegime.STRONG, SimulationConfig())
    assert weights["breakout"] > weights["rebound"]


def test_user_override_weights():
    cfg = SimulationConfig(strategy_category_weights={"breakout": 2.0})
    weights = get_weights(MarketRegime.NEUTRAL, cfg)
    assert weights["breakout"] == 2.0


def test_default_weights_structure():
    """确认每个市场环境下都包含五个战法类别权重。"""
    categories = {"breakout", "pattern", "rebound", "stage", "risk"}
    for regime in MarketRegime:
        assert set(DEFAULT_ENVIRONMENT_WEIGHTS[regime]) == categories


def test_weak_favors_rebound():
    """弱势环境下反弹权重应高于突破权重。"""
    weights = get_weights(MarketRegime.WEAK, SimulationConfig())
    assert weights["rebound"] > weights["breakout"]
