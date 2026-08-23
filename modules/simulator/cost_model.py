#!/usr/bin/env python3
"""
真实交易成本模型。

- 佣金：双向收取，最低 5 元
- 印花税：卖出方单向收取，默认千 0.5
- 过户费：双向万 0.1（沪市标准简化）
"""

from __future__ import annotations

from . import CostModel


def calculate_costs(amount: float, action: str, cost_model: CostModel) -> dict[str, float]:
    """
    计算单笔交易成本。

    Args:
        amount: 成交金额
        action: "BUY" / "SELL" / "PARTIAL_SELL"
        cost_model: 成本模型

    Returns:
        {"commission": 佣金, "stamp_duty": 印花税, "transfer_fee": 过户费, "total": 总费用}
    """
    commission = max(amount * cost_model.commission_rate, cost_model.min_commission)
    transfer_fee = amount * cost_model.transfer_fee_rate

    stamp_duty = 0.0
    if action in ("SELL", "PARTIAL_SELL") and cost_model.apply_stamp_duty_on_sell:
        stamp_duty = amount * cost_model.stamp_duty_rate

    return {
        "commission": round(commission, 2),
        "stamp_duty": round(stamp_duty, 2),
        "transfer_fee": round(transfer_fee, 2),
        "total": round(commission + stamp_duty + transfer_fee, 2),
    }
