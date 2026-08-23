"""股票评分格式化。"""

from .models import StockScore


def format_stock_score(score: StockScore) -> str:
    """格式化股票评分"""
    return f"""
{score.ts_code} {score.name}
{"=" * 50}
综合评分: {score.score:.1f}/100 {score.rating}
{"=" * 50}
B1买点评分: {score.b1_score:.1f}
趋势评分: {score.trend_score:.1f}
量价评分: {score.volume_score:.1f}
风险评分: {score.risk_score:.1f}

利好因素:
{chr(10).join(f"  + {r}" for r in score.reasons) if score.reasons else "  无"}

风险提示:
{chr(10).join(f"  ! {w}" for w in score.warnings) if score.warnings else "  无"}
"""
