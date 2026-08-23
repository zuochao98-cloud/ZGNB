#!/usr/bin/env python3
"""战法共振评分层单元测试。"""

from __future__ import annotations

from modules.simulator import RawStrategySignal, SimulationConfig, SignalVerdict
from modules.simulator.resonance_scorer import calculate_resonance, apply_weights


def test_b1_b2_resonance_increases_score():
    raw = [
        RawStrategySignal("B1", "rebound", "BUY", 0.8, "20240101"),
        RawStrategySignal("B2", "breakout", "BUY", 0.7, "20240101"),
    ]
    score = calculate_resonance(raw, "000001.SZ", "测试", "20240101", SimulationConfig())
    assert score.verdict.value == "通过"
    assert score.total_score > 1.0


def test_sprint_stage_triggers_high_risk():
    raw = [
        RawStrategySignal("B1", "rebound", "BUY", 0.8, "20240101"),
        RawStrategySignal("三波冲刺", "stage", "SELL", 0.9, "20240101"),
    ]
    score = calculate_resonance(raw, "000001.SZ", "测试", "20240101", SimulationConfig())
    assert score.verdict == SignalVerdict.HIGH_RISK


def test_low_score_returns_no_signal():
    raw = [RawStrategySignal("量比攻击", "breakout", "WATCH", 0.3, "20240101")]
    score = calculate_resonance(raw, "000001.SZ", "测试", "20240101", SimulationConfig())
    assert score.verdict == SignalVerdict.NO_SIGNAL


def test_apply_weights_identity_fallback():
    raw = [
        RawStrategySignal("B1", "rebound", "BUY", 0.8, "20240101"),
        RawStrategySignal("B2", "breakout", "BUY", 0.7, "20240101"),
    ]
    score = calculate_resonance(raw, "000001.SZ", "测试", "20240101", SimulationConfig())
    assert apply_weights(score, {}) == score.total_score
    assert apply_weights(score, {"rebound": 2.0, "breakout": 0.5}) == score.total_score
