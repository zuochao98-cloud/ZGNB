"""
交割单模块
只负责数据准备，不生成点评（点评由 LLM 用 Z哥角色输出）
"""

from typing import Optional
import logging
from dataclasses import dataclass
from datetime import datetime

from .database import save_trade_record, get_trade_records
from .indicators import analyze_stock
from .trade_parser import TradeParser, ParseResult
from .core.errors import ErrorCode, ZettarancError

logger = logging.getLogger(__name__)

# 黑话词典（LLM 生成点评时可用）
JARGON_DICT = {
    "卤煮": "落袋为安，赚钱后卖出",
    "建仓": "试探性买入，轻仓",
    "卖飞": "卖出后股价继续大涨",
    "B1": "买点1，J值<-10的买入信号",
    "B2": "买点2，放量突破确认的买入信号",
    "B3": "买点3，分歧转一致的中继买点",
    "SB1": "超级B1，震仓后的买点",
    "长安战法": "三日确认战法，胜率75%",
    "S1": "卖出信号1，放量大跌阴线",
    "S2": "卖出信号2，防卖飞预警",
    "四块砖": "砖型图连续4根红砖减半仓",
    "白线": "Z哥白线，强势股趋势线",
    "大哥线": "知行多空线，主力成本线",
    "碗": "白线和黄线之间的区域",
    "单针下20": "深V反弹信号，超跌后快速反弹",
}

TRADE_REVIEW_PROMPT = """你以 zettaranc（Z哥）的身份点评用户的交易记录。

**风格要求**：
- 直接、犀利、不废话
- 常用反问句确认用户理解
- 结尾用金句收尾
- 可以用黑话：卤煮=落袋为安、建仓=试探仓位、卖飞=卖出后大涨
- 参考语料库中的表达方式

**点评维度**：
- 买点：是否符合战法、时机如何、J值位置、BBI位置
- 卖点：是否卤煮、是否止损、是否卖飞
- 完整交易：盈亏、持仓天数、买卖点是否准确
- 仓位建议

**禁止**：
- 不要模板化输出
- 不要分点列表太多（超过5点）
- 不要用"首先...其次..."这种套路
"""


@dataclass
class ReviewContext:
    """点评上下文 - 准备给 LLM 的数据包"""

    # 基础交易信息
    ts_code: str
    name: str
    trade_date: str
    action: str  # BUY/SELL
    price: float
    quantity: int
    amount: float
    reason: str

    # 计算数据（买点/卖点特有）
    avg_cost: float | None = None  # 对于卖出，计算平均成本
    profit_pct: float | None = None  # 对于卖出，计算盈亏比例
    holding_days: int | None = None  # 持仓天数

    # 指标数据（获取当时的）
    indicators: dict | None = None  # 当时的技术指标

    # 对应交易
    matched_buy: dict | None = None  # 对于卖出，找对应的买入
    matched_sell: dict | None = None  # 对于买入，找对应的卖出

    # 元数据
    is_complete_trade: bool = False  # 是否是完整交易（有买有卖）
    signal_type: str | None = None  # 卤煮/止损/卖飞/建仓
    tags: list[str] | None = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    def to_llm_prompt(self) -> str:
        """转换为给 LLM 的提示词"""
        parts = ["【交易记录】"]

        # 基础信息
        action_text = "买入" if self.action == "BUY" else "卖出"
        parts.append(f"股票: {self.name} ({self.ts_code})")
        parts.append(f"日期: {self.trade_date}")
        parts.append(f"操作: {action_text}")
        parts.append(f"价格: {self.price}元")
        parts.append(f"数量: {self.quantity}股")
        parts.append(f"金额: {self.amount}元")
        parts.append(f"原因: {self.reason}")

        # 盈亏（如果是卖出）
        if self.action == "SELL" and self.profit_pct is not None:
            if self.profit_pct >= 0:
                parts.append(f"收益: 盈利{self.profit_pct:.1f}%")
            else:
                parts.append(f"收益: 亏损{abs(self.profit_pct):.1f}%")

        # 持仓天数
        if self.holding_days is not None:
            parts.append(f"持仓天数: {self.holding_days}天")

        # 信号类型
        if self.signal_type:
            parts.append(f"信号类型: {self.signal_type}")

        # 指标数据
        if self.indicators:
            ind = self.indicators
            parts.append("")
            parts.append("【当时技术指标】")
            if "j" in ind and ind["j"]:
                parts.append(f"J值: {ind['j']:.1f}")
            if "k" in ind and ind["k"]:
                parts.append(f"KDJ: K={ind['k']:.1f} D={ind['d']:.1f}")
            if "bbi" in ind and ind["bbi"]:
                parts.append(f"BBI: {ind['bbi']:.2f}")
            if "signal" in ind:
                parts.append(f"信号: {ind['signal']}")
            if "sell_score" in ind:
                parts.append(f"防卖飞评分: {ind['sell_score']}/5")

        # 完整交易信息
        if self.is_complete_trade:
            parts.append("")
            parts.append("【这是完整的一笔交易】")
            if self.matched_buy:
                parts.append(f"买入价: {self.matched_buy.get('price')}元")
            if self.matched_sell:
                parts.append(f"卖出价: {self.matched_sell.get('price')}元")

        # 标签
        if self.tags:
            parts.append(f"标签: {', '.join(self.tags)}")

        return "\n".join(parts)

    def get_full_prompt(self) -> str:
        """获取完整的 LLM 提示词（包含角色提示 + 数据）"""
        return f"{TRADE_REVIEW_PROMPT}\n\n---\n\n{self.to_llm_prompt()}\n\n---\n\n请以 Z哥的口吻点评这笔交易。"

    def get_jargon_hint(self) -> str:
        """获取黑话提示"""
        hints = [f"- {k}: {v}" for k, v in JARGON_DICT.items()]
        return "黑话提示：\n" + "\n".join(hints)


class TradeReviewer:
    """交割单 - 数据准备层"""

    def __init__(self) -> None:
        self.parser = TradeParser()

    def parse_input(self, text: str) -> tuple[ParseResult, dict | None]:
        """
        解析用户输入
        Returns: (解析结果, 状态数据)
        """
        result = self.parser.parse(text)
        return result, result.data

    def prepare_review_context(
        self, data: dict, action_type: str | None = None, extra_info: dict | None = None
    ) -> ReviewContext:
        """
        准备点评上下文

        Args:
            data: 解析后的交易数据
            action_type: 交易类型 BUY/SELL
            extra_info: 额外信息（如卤煮/止损/建仓等）
        """
        ctx = ReviewContext(
            ts_code=data.get("ts_code", ""),
            name=data.get("name", data.get("ts_code", "")),
            trade_date=data.get("trade_date", datetime.now().strftime("%Y-%m-%d")),
            action=action_type or data.get("action", "BUY"),
            price=data.get("price", 0),
            quantity=data.get("quantity", 0),
            amount=data.get("amount", 0),
            reason=data.get("reason", ""),
        )

        # 如果有额外信息
        if extra_info:
            if "signal_type" in extra_info:
                ctx.signal_type = extra_info["signal_type"]
            if "tags" in extra_info:
                ctx.tags = extra_info["tags"]

        return ctx

    def enrich_with_indicators(self, ctx: ReviewContext, days: int = 60) -> ReviewContext:
        """补充当时的技术指标数据

        指标获取为可选：失败时记录日志，跳过指标补充，调用方可继续走无指标路径。
        """
        try:
            result = analyze_stock(ctx.ts_code, days=days)
            if result:
                ctx.indicators = {
                    "j": getattr(result, "j", None),
                    "k": getattr(result, "k", None),
                    "d": getattr(result, "d", None),
                    "bbi": getattr(result, "bbi", None),
                    "signal": getattr(result, "signal", None),
                    "sell_score": getattr(result, "sell_score", None),
                    "pct_chg": getattr(result, "pct_chg", None),
                }
        except (ZettarancError, ValueError, KeyError, AttributeError) as e:
            logger.warning(
                "[trade_reviewer] 获取指标失败 (code=%s, ts_code=%s): %s",
                ErrorCode.TRADE_REVIEW_FAILED.value,
                ctx.ts_code,
                e,
            )

        return ctx

    def enrich_with_buy_info(self, ctx: ReviewContext) -> ReviewContext:
        """对于卖出，补充买入信息和盈亏计算"""
        trades = get_trade_records(ts_code=ctx.ts_code, limit=100)
        buy_trades = [t for t in trades if t.get("action") == "BUY"]

        if buy_trades:
            # 计算平均成本
            total_amount = sum(t.get("amount", 0) for t in buy_trades)
            total_qty = sum(t.get("quantity", 0) for t in buy_trades)
            ctx.avg_cost = total_amount / total_qty if total_qty > 0 else 0

            # 计算盈亏
            if ctx.price > 0 and ctx.avg_cost > 0:
                ctx.profit_pct = ((ctx.price - ctx.avg_cost) / ctx.avg_cost) * 100

            # 计算持仓天数（第一笔买入到卖出）
            first_buy = buy_trades[-1]
            if first_buy.get("trade_date") and ctx.trade_date:
                try:
                    d1 = datetime.strptime(first_buy["trade_date"], "%Y-%m-%d")
                    d2 = datetime.strptime(ctx.trade_date, "%Y-%m-%d")
                    ctx.holding_days = (d2 - d1).days
                except (ValueError, TypeError) as e:
                    # 日期格式异常：放弃持仓天数计算（非关键字段）
                    logger.debug("[trade_reviewer] 日期解析失败，跳过 holding_days: %s", e)
                    pass

            ctx.matched_buy = {"price": ctx.avg_cost, "date": first_buy.get("trade_date"), "quantity": total_qty}

        return ctx

    def check_if_complete_trade(self, ctx: ReviewContext) -> ReviewContext:
        """检查是否有对应的买卖交易"""
        trades = get_trade_records(ts_code=ctx.ts_code, limit=100)

        if ctx.action == "BUY":
            # 查找是否有卖出
            sell_trades = [t for t in trades if t.get("action") == "SELL"]
            if sell_trades:
                ctx.is_complete_trade = True
                ctx.matched_sell = sell_trades[0]
        else:
            # 查找是否有买入
            buy_trades = [t for t in trades if t.get("action") == "BUY"]
            if buy_trades:
                ctx.is_complete_trade = True

        return ctx

    def save_trade(self, ctx: ReviewContext) -> int:
        """保存交易记录"""
        record = {
            "ts_code": ctx.ts_code,
            "trade_date": ctx.trade_date,
            "action": ctx.action,
            "price": ctx.price,
            "quantity": ctx.quantity,
            "amount": ctx.amount,
            "reason": ctx.reason,
            "signal_type": ctx.signal_type or "",
            "tags": ",".join(ctx.tags) if ctx.tags else "",
        }
        return save_trade_record(record)


def create_reviewer() -> TradeReviewer:
    """创建复盘器实例"""
    return TradeReviewer()


# 全局实例
reviewer = TradeReviewer()
