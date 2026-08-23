"""每日五步工作流。"""

from typing import Any

from .engine import screen_stocks
from .market import get_market_status


def daily_workflow() -> dict[str, Any]:
    """
    每日五步工作流

    返回分析结果
    """
    print("=" * 60)
    print("Z哥 每日五步工作流")
    print("=" * 60)

    # Step 1: 择时（1分钟）
    print("\n[Step 1] 择时判断")
    market = get_market_status()
    print(f"大盘状态: {market.market_direction}")
    print(f"市场强度: {market.market_strength}/100")
    for reason in market.reasons:
        print(f"  - {reason}")

    if market.market_direction == "SHORT":
        print("  => 建议: 轻仓或空仓观望")

    # Step 2: 定策略（2分钟）
    print("\n[Step 2] 策略制定")
    if market.market_direction == "LONG":
        print("  => 多头策略: 主攻")
    elif market.market_direction == "SHORT":
        print("  => 空头策略: 防守")
    else:
        print("  => 中性策略: 观望/底仓不动")

    # Step 3: 选股（5分钟）
    print("\n[Step 3] 选股")
    b1_stocks = screen_stocks("b1")[:5]
    perfect_stocks = screen_stocks("perfect")[:5]

    print("B1买点机会 (TOP 5):")
    for i, s in enumerate(b1_stocks[:5], 1):
        print(f"  {i}. {s.ts_code} {s.name} 评分:{s.score:.0f}")

    print("\n完美图形 (TOP 5):")
    for i, s in enumerate(perfect_stocks[:5], 1):
        print(f"  {i}. {s.ts_code} {s.name} 评分:{s.score:.0f}")

    # Step 4: 执行计划
    print("\n[Step 4] 执行计划")
    print("  - 严格按条件执行，不临时改变")
    print("  - 量比战法/B1/滴滴战法对应触发条件")

    # Step 5: 复盘准备
    print("\n[Step 5] 复盘准备")
    print("  - 记录今日操作")
    print("  - 明日重点关注股票")

    return {
        "market": market,
        "b1_opportunities": b1_stocks[:5],
        "perfect_patterns": perfect_stocks[:5],
    }
