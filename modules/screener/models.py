"""选股评分数据模型。"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class StockScore:
    """股票评分"""

    ts_code: str
    name: str = ""
    score: float = 0  # 综合评分 0-100
    b1_score: float = 0  # B1买点评分
    trend_score: float = 0  # 趋势评分
    volume_score: float = 0  # 量价评分
    risk_score: float = 0  # 风险评分
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def rating(self) -> str:
        """评级"""
        if self.score >= 80:
            return "★★★★★ 强烈推荐"
        elif self.score >= 65:
            return "★★★★☆ 推荐"
        elif self.score >= 50:
            return "★★★☆☆ 可关注"
        elif self.score >= 35:
            return "★★☆☆☆ 谨慎"
        else:
            return "★☆☆☆☆ 不推荐"


@dataclass
class MarketStatus:
    """大盘状态"""

    trade_date: str
    is_trading: bool = True  # 是否可交易
    market_direction: str = "NEUTRAL"  # LONG/NEUTRAL/SHORT
    market_strength: float = 0  # 0-100
    reasons: list[str] = field(default_factory=list)
