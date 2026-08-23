#!/usr/bin/env python3
"""
动态滑点模型。

根据 ATR 波动率与成交量萎缩程度，动态调整买卖滑点。
"""

from __future__ import annotations

from ..indicators import DailyData
from . import SimulationConfig


def _atr(klines: list[DailyData], window: int = 20) -> float:
    """计算最近 window 日的平均真实波幅（ATR）。"""
    if len(klines) < window + 1:
        return 0.0
    trs: list[float] = []
    for i in range(1, window + 1):
        k = klines[-i]
        prev = klines[-i - 1]
        tr = max(k.high - k.low, abs(k.high - prev.close), abs(k.low - prev.close))
        trs.append(tr)
    return sum(trs) / len(trs)


def calculate_slippage(
    kline: DailyData,
    klines: list[DailyData],
    action: str,
    config: SimulationConfig,
) -> float:
    """
    计算单根 K 线对应的滑点。

    Args:
        kline: 当前成交日 K 线
        klines: 历史 K 线序列（含当前日）
        action: "BUY" / "SELL" / "PARTIAL_SELL"
        config: 模拟器配置

    Returns:
        滑点比例（如 0.001 表示 0.1%）
    """
    if not config.use_dynamic_slippage:
        return config.slippage

    base = config.slippage_model.base_slippage
    atr_value = _atr(klines, config.atr_window)
    price = kline.close or kline.open
    volatility_component = (atr_value / price) * config.slippage_model.volatility_multiplier if price else 0.0

    # 量比惩罚：成交量低于 20 日均量 50%
    if len(klines) >= 21:
        avg_vol = sum(k.vol for k in klines[-21:-1]) / 20
        if avg_vol > 0 and kline.vol / avg_vol < 0.5:
            volatility_component += config.slippage_model.volume_penalty

    return base + volatility_component
