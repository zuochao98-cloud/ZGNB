#!/usr/bin/env python3
"""
战法共振评分层。

对单只股票当日可见的战法信号做聚合评分，识别共振与冲突，
输出统一的 ResonanceScore 供 signal_filter 进一步过滤。
"""

from __future__ import annotations

from . import RawStrategySignal, ResonanceScore, SimulationConfig, SignalVerdict
from ..constants import PARAM_STEP_COARSE


# 类别组合共振奖励
CATEGORY_RESONANCE_BONUS: dict[tuple[str, str], float] = {
    ("rebound", "breakout"): 0.15,
    ("rebound", "pattern"): PARAM_STEP_COARSE,
    ("breakout", "stage"): PARAM_STEP_COARSE,
    ("rebound", "stage"): PARAM_STEP_COARSE,
}


# 直接触发 HIGH_RISK 的 strategy 列表
RISK_STRATEGIES: set[str] = {
    "三波冲刺",
    "麒麟派发",
    "出货五式",
    "顶部大风车",
    "S1",
    "S2",
    "S3",
    "绿肥红瘦",
    "阶梯放量下跌",
}


def _category_resonance_bonus(categories: set[str]) -> float:
    """根据同时出现的类别组合给予额外奖励。"""
    bonus = 0.0
    for (a, b), value in CATEGORY_RESONANCE_BONUS.items():
        if a in categories and b in categories:
            bonus += value
    return bonus


def calculate_resonance(
    raw_signals: list[RawStrategySignal],
    ts_code: str,
    name: str,
    date: str,
    config: SimulationConfig,
) -> ResonanceScore:
    """
    计算战法共振评分。

    Args:
        raw_signals: 已过滤且去重的 RawStrategySignal 列表
        ts_code: 股票代码
        name: 股票名称
        date: 当前交易日
        config: 模拟配置

    Returns:
        ResonanceScore
    """
    buy_score = 0.0
    risk_score = 0.0
    matched: list[str] = []
    conflicts: list[str] = []
    categories: set[str] = set()

    for s in raw_signals:
        matched.append(s.strategy)
        categories.add(s.category)

        if s.action == "BUY":
            buy_score += s.confidence
        elif s.action == "SELL":
            risk_score += s.confidence
        elif s.action == "WATCH":
            buy_score += s.confidence * 0.3
        elif s.action == "HOLD":
            buy_score += s.confidence * 0.1

        if s.strategy in RISK_STRATEGIES:
            conflicts.append(f"{s.strategy}：风险信号")

    # 类别共振奖励
    buy_score += _category_resonance_bonus(categories)

    total_score = buy_score - risk_score

    # verdict 判定
    if conflicts:
        verdict = SignalVerdict.HIGH_RISK
    elif total_score < config.min_resonance_score:
        verdict = SignalVerdict.NO_SIGNAL
    else:
        verdict = SignalVerdict.PASS

    return ResonanceScore(
        ts_code=ts_code,
        name=name,
        date=date,
        total_score=round(total_score, 4),
        buy_score=round(buy_score, 4),
        risk_score=round(risk_score, 4),
        matched_strategies=matched,
        conflicts=conflicts,
        verdict=verdict,
    )


def apply_weights(resonance: ResonanceScore, weights: dict[str, float]) -> float:
    """
    将共振分按环境权重加权。

    当前实现：按 buy_score 与 risk_score 分别加权后相减。
    类别权重在 signal_filter 中通过 per-strategy 加权实现，此处保持简单。
    """
    # 默认权重为 1.0
    return resonance.total_score
