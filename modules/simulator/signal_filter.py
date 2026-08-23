#!/usr/bin/env python3
"""
信号过滤模块。

对 screener 评分结果或战法共振信号进行二次过滤：
- simple 模式：综合评分 >= threshold，至少触发 N 个共振标签，风险不过高
- resonance 模式：调用 modules.strategies 检测战法，经适配、去重、加权后
  计算战法共振分，输出 SignalScore
"""

from __future__ import annotations

import logging

from ..screener import StockScore, analyze_stock
from ..datasource import DataSource, get_datasource
from ..indicators import DailyData, calculate_sandglass_score
from ..indicators.volume_patterns import detect_volume_ratio_strategy
from ..indicators.price_patterns import detect_bull_rope
from ..strategies import detect_all_strategies
from . import (
    SignalScore,
    SignalVerdict,
    SimulationConfig,
    MarketContext,
    MarketRegime,
    RawStrategySignal,
)
from .strategy_adapter import adapt, filter_by_date, deduplicate
from .resonance_scorer import calculate_resonance
from .environment_weights import get_weights


logger = logging.getLogger(__name__)


_REQUIRED_SIGNALS = ("B1", "沙漏完美", "量比攻击", "牛绳金叉")


def _extract_signals(score: StockScore, klines: list[DailyData]) -> list[str]:
    """从 StockScore 和原始 K 线中提取共振标签（v0.2 simple 模式）。"""
    signals: list[str] = []
    reasons = " ".join(score.reasons)
    warnings = " ".join(score.warnings)

    if score.b1_score >= 60 or "B1" in reasons:
        signals.append("B1")

    # 沙漏完美
    try:
        sg = calculate_sandglass_score(klines)
        if sg.get("is_perfect"):
            signals.append("沙漏完美")
        elif sg.get("score", 0) >= 70:
            signals.append("沙漏良好")
    except (KeyError, AttributeError, TypeError, ValueError, IndexError) as e:
        # 调用方通过 signals 列表缺失回退为无标签，自然降级为不附加该信号
        logger.warning("[signal_filter] 计算沙漏分失败，跳过沙漏信号: %s", e)

    # 量比战法
    try:
        vr = detect_volume_ratio_strategy(klines)
        scene = vr.get("scene", "")
        if scene in ("攻击日", "超级攻击", "单向拉升"):
            signals.append("量比攻击")
        elif scene in ("出货日", "弱势日"):
            signals.append("量比恶劣")
    except (KeyError, AttributeError, TypeError, ValueError, IndexError) as e:
        # 调用方通过 signals 列表缺失回退为无标签，自然降级为不附加该信号
        logger.warning("[signal_filter] 量比战法检测失败，跳过量比信号: %s", e)

    # 牛绳
    try:
        br = detect_bull_rope(klines)
        if br.get("signal") == "牵牛":
            signals.append("牛绳金叉")
        elif br.get("signal") == "牛绳断":
            signals.append("牛绳断")
    except (KeyError, AttributeError, TypeError, ValueError, IndexError) as e:
        # 调用方通过 signals 列表缺失回退为无标签，自然降级为不附加该信号
        logger.warning("[signal_filter] 牛绳检测失败，跳过牛绳信号: %s", e)

    # 三波 / 麒麟会阶段（从 reason/warning 推断）
    if "建仓波" in reasons:
        signals.append("建仓波")
    if "吸筹" in reasons:
        signals.append("吸筹")
    if "冲刺波" in warnings or "派发" in warnings:
        signals.append("高风险阶段")

    return signals


def _evaluate_resonance(
    ts_code: str,
    trade_date: str,
    name: str,
    klines: list[DailyData],
    context: MarketContext | None,
    config: SimulationConfig,
) -> SignalScore:
    """resonance 模式：使用 modules.strategies 检测战法并计算共振分。"""
    raw_signals = adapt(detect_all_strategies(ts_code, days=120))
    recent = filter_by_date(raw_signals, trade_date, config.strategy_lookback_days)
    recent = deduplicate(recent)

    weights = get_weights(context.regime if context else MarketRegime.NEUTRAL, config)
    weighted = [
        RawStrategySignal(
            strategy=s.strategy,
            category=s.category,
            action=s.action,
            confidence=s.confidence * weights.get(s.category, 1.0),
            trade_date=s.trade_date,
            reason=s.reason,
        )
        for s in recent
    ]

    resonance = calculate_resonance(weighted, ts_code, name, trade_date, config)

    # 将 resonance.total_score 映射到 0-100
    mapped_score = max(0.0, min(100.0, resonance.total_score * 50 + 50))

    return SignalScore(
        ts_code=ts_code,
        name=name,
        date=trade_date,
        score=mapped_score,
        b1_score=0.0,
        trend_score=0.0,
        volume_score=0.0,
        risk_score=resonance.risk_score * 50,
        signals=resonance.matched_strategies,
        reasons=[f"共振分 {resonance.total_score:.2f}"] + resonance.conflicts,
        warnings=resonance.conflicts,
        verdict=resonance.verdict,
        resonance=resonance,
    )


def evaluate_stock(
    ts_code: str,
    trade_date: str,
    klines: list[DailyData] | None = None,
    datasource: DataSource | None = None,
    config: SimulationConfig | None = None,
    context: MarketContext | None = None,
) -> SignalScore:
    """
    评估单只股票在某交易日的信号质量。

    Args:
        ts_code: 股票代码
        trade_date: 当前日期
        klines: 可选，外部传入 K 线
        datasource: 数据源
        config: 模拟配置；为空时使用默认配置
        context: 当前市场环境

    Returns:
        SignalScore
    """
    config = config or SimulationConfig()

    if config.strategy_mode == "resonance":
        return _evaluate_resonance(ts_code, trade_date, ts_code, klines or [], context, config)

    # simple 模式保持 v0.2 原逻辑
    ds = datasource or get_datasource()
    if klines is None:
        from ..screener.data import get_recent_klines

        klines = get_recent_klines(ts_code, 150, datasource=ds)

    if not klines or len(klines) < 60:
        return SignalScore(
            ts_code=ts_code,
            name=ts_code,
            date=trade_date,
            score=0,
            b1_score=0,
            trend_score=0,
            volume_score=0,
            risk_score=0,
            signals=[],
            reasons=[],
            warnings=["数据不足"],
            verdict=SignalVerdict.NO_SIGNAL,
        )

    score = analyze_stock(ts_code, klines=klines, datasource=ds)
    signals = _extract_signals(score, klines)

    verdict = SignalVerdict.PASS
    threshold = config.position_score_threshold if config else 60.0
    if score.score < threshold:
        verdict = SignalVerdict.LOW_SCORE
    elif "高风险阶段" in signals:
        verdict = SignalVerdict.HIGH_RISK
    elif "牛绳断" in signals or "量比恶劣" in signals:
        verdict = SignalVerdict.BAD_STAGE
    elif "B1" not in signals:
        verdict = SignalVerdict.NO_SIGNAL

    return SignalScore(
        ts_code=ts_code,
        name=score.name or ts_code,
        date=trade_date,
        score=score.score,
        b1_score=score.b1_score,
        trend_score=score.trend_score,
        volume_score=score.volume_score,
        risk_score=score.risk_score,
        signals=signals,
        reasons=score.reasons,
        warnings=score.warnings,
        verdict=verdict,
    )


def filter_signals(
    scores: list[SignalScore],
    score_threshold: float = 70.0,
    min_signal_count: int = 2,
) -> list[SignalScore]:
    """
    过滤并排序候选信号。

    过滤条件：
    - verdict == PASS
    - score >= score_threshold
    - 有效共振标签数 >= min_signal_count
    """

    def _effective_signals(s: SignalScore) -> int:
        positive = {"B1", "沙漏完美", "沙漏良好", "量比攻击", "牛绳金叉", "建仓波", "吸筹"}
        return len(positive.intersection(s.signals))

    filtered = [
        s
        for s in scores
        if s.verdict == SignalVerdict.PASS and s.score >= score_threshold and _effective_signals(s) >= min_signal_count
    ]
    filtered.sort(key=lambda x: (x.score, _effective_signals(x)), reverse=True)
    return filtered
