#!/usr/bin/env python3
"""
Z哥投资账本 MCP Server
======================

基于 MCP (Model Context Protocol) 协议，为 AI 工具提供投资账本能力：
  - 交易记录管理（口语化解析、CRUD、统计）
  - 自选股管理（增删、信号扫描、日报生成）
  - 持仓诊断（单票完整诊断）
  - 选股筛选（多策略选股）

使用方式：
  # 方式 1：CLI 运行（stdio 模式，适合 Claude Desktop / Cursor）
  python mcp_server.py

  # 方式 2：直接调用（FastMCP 实例可被其他 Python 程序引用）
  from mcp_server import mcp

v1.0 · 2026-11-10
"""

from __future__ import annotations

import sys
import logging
from typing import Any

# ── 路径设置（确保 modules/ 可导入）───────────────────────────────────────────
from pathlib import Path

_project_root = Path(__file__).parent.resolve()
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# ── 日志配置 ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("investment-ledger-mcp")

# ── MCP 服务器实例 ─────────────────────────────────────────────────────────────
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="investment-ledger",
    instructions=(
        "Z哥投资账本 MCP 服务器。"
        "提供交易记录管理（口语化解析、CRUD、盈亏统计）、自选股管理（增删、信号扫描、日报）、"
        "持仓诊断（K线形态、防卖飞评分、出货/买入信号）、选股筛选（B1/B2/B3/长安战法等）。"
        "所有数据存储在本地 SQLite 数据库中，不依赖外部 API。"
    ),
)


# =============================================================================
# 交易记录管理工具
# =============================================================================


@mcp.tool()
def parse_trade(text: str) -> dict[str, Any]:
    """
    解析口语化交易描述为结构化数据（不保存）。

    支持多种格式：
      - "今天10:30买入600519.SH 茅台 100股 成交价1680"
      - "600487.SH 通光线缆 周五涨停买入500股"
      - "卖出 300750 宁德时代 200股"

    Args:
        text: 口语化交易描述文本

    Returns:
        解析结果字典，包含 success / confidence / data / missing_fields
    """
    from modules.trade_parser import TradeParser

    parser = TradeParser()
    result = parser.parse(text)

    return {
        "success": result.success,
        "confidence": result.confidence,
        "data": result.data,
        "missing_fields": result.missing_fields,
        "error_message": result.error_message,
    }


@mcp.tool()
def add_trade(text: str) -> dict[str, Any]:
    """
    解析并保存一条交易记录。

    Args:
        text: 口语化交易描述（如 "今天买入600519.SH 茅台 100股 1680元"）

    Returns:
        保存结果，包含记录 ID 和解析出的数据
    """
    from modules.trade_parser import TradeParser
    from modules.trade_manager import TradeManager

    parser = TradeParser()
    parse_result = parser.parse(text)

    if not parse_result.success or not parse_result.data:
        return {
            "success": False,
            "error": parse_result.error_message or "解析失败",
            "missing_fields": parse_result.missing_fields,
        }

    # 检查关键字段完整性
    if parse_result.missing_fields:
        return {
            "success": False,
            "error": f"缺少必要字段: {', '.join(parse_result.missing_fields)}",
            "missing_fields": parse_result.missing_fields,
            "parsed_data": parse_result.data,
            "hint": "请补充价格信息，如 '买入 600519.SH 茅台 100股 1680元'",
        }

    tm = TradeManager()
    record_id = tm.add_trade(parse_result.data)

    logger.info("添加交易记录 #%d: %s %s", record_id, parse_result.data.get("ts_code"), parse_result.data.get("action"))

    return {
        "success": True,
        "id": record_id,
        "data": parse_result.data,
    }


@mcp.tool()
def list_trades(page: int = 1, page_size: int = 20, ts_code: str | None = None) -> dict[str, Any]:
    """
    分页查询交易记录列表。

    Args:
        page: 页码（从 1 开始）
        page_size: 每页条数（默认 20，最大 100）
        ts_code: 可选，按股票代码筛选（如 600519.SH）

    Returns:
        包含 records / total / page / page_size 的字典
    """
    from modules.trade_manager import TradeManager

    tm = TradeManager()
    result = tm.list_all_trades(page=page, page_size=page_size)

    records = []
    for r in result.get("records", []):
        if ts_code and r.get("ts_code") != ts_code:
            continue
        records.append({
            "id": r.get("id"),
            "ts_code": r.get("ts_code"),
            "trade_date": r.get("trade_date"),
            "action": r.get("action"),
            "price": r.get("price"),
            "quantity": r.get("quantity"),
            "amount": r.get("amount"),
            "reason": r.get("reason"),
            "signal_type": r.get("signal_type"),
            "zg_review": r.get("zg_review"),
            "tags": r.get("tags"),
            "notes": r.get("notes"),
        })

    return {
        "total": result.get("total", len(records)),
        "page": page,
        "page_size": page_size,
        "records": records,
    }


@mcp.tool()
def update_trade(trade_id: int, updates: dict[str, Any]) -> dict[str, Any]:
    """
    更新交易记录的指定字段。

    Args:
        trade_id: 交易记录 ID
        updates: 要更新的字段字典（如 {"notes": "加仓", "reason": "B1 买点"}）

    Returns:
        更新结果
    """
    from modules.database import update_trade_record

    success = update_trade_record(trade_id, updates)
    return {
        "status": "ok" if success else "not_found",
        "trade_id": trade_id,
        "updated_fields": list(updates.keys()),
    }


@mcp.tool()
def delete_trade(trade_id: int) -> dict[str, Any]:
    """
    删除一条交易记录。

    Args:
        trade_id: 交易记录 ID

    Returns:
        删除结果
    """
    from modules.database import delete_trade_record

    success = delete_trade_record(trade_id)
    return {
        "status": "ok" if success else "not_found",
        "trade_id": trade_id,
    }


@mcp.tool()
def get_trade_stats(ts_code: str | None = None) -> dict[str, Any]:
    """
    获取交易统计：汇总 + 盈亏。

    Args:
        ts_code: 可选，按股票代码筛选。不传则返回全部汇总。

    Returns:
        包含 summary 和 pnl 的统计字典
    """
    from modules.trade_manager import TradeManager

    tm = TradeManager()
    summary = tm.get_summary(ts_code=ts_code)
    pnl = tm.calculate_pnl(ts_code=ts_code)

    return {
        "summary": summary,
        "pnl": pnl,
    }


@mcp.tool()
def get_holding(ts_code: str) -> dict[str, Any]:
    """
    查询某只股票的当前持仓情况。

    Args:
        ts_code: 股票代码（如 600519.SH）

    Returns:
        持仓信息：总买入/卖出、当前持仓数量、平均成本、已实现盈亏等
    """
    from modules.trade_manager import TradeManager

    tm = TradeManager()
    return tm.get_stock_holding(ts_code)


# =============================================================================
# 自选股管理工具
# =============================================================================


@mcp.tool()
def list_watchlist(tags: str | None = None) -> dict[str, Any]:
    """
    列出自选股列表。

    Args:
        tags: 可选，按标签筛选（逗号分隔）

    Returns:
        自选股列表
    """
    from modules.watchlist import list_watch

    items = list_watch(tags=tags)
    result_items = []
    for item in items:
        result_items.append({
            "id": item.get("id"),
            "ts_code": item.get("ts_code"),
            "name": item.get("name"),
            "tags": item.get("tags"),
            "notes": item.get("notes"),
            "added_date": item.get("added_date"),
            "alert_enabled": item.get("alert_enabled", True),
        })

    return {"count": len(result_items), "items": result_items}


@mcp.tool()
def add_watchlist(ts_code: str, tags: str = "", notes: str = "") -> dict[str, Any]:
    """
    添加股票到自选股列表。

    Args:
        ts_code: 股票代码（如 600519.SH）
        tags: 标签（逗号分隔，如 "核心仓,B1"）
        notes: 备注说明

    Returns:
        添加结果
    """
    from modules.watchlist import add_watch

    row_id = add_watch(ts_code, tags=tags, notes=notes)
    return {"status": "ok", "id": row_id, "ts_code": ts_code}


@mcp.tool()
def remove_watchlist(ts_code: str) -> dict[str, Any]:
    """
    从自选股移除股票。

    Args:
        ts_code: 股票代码

    Returns:
        移除结果
    """
    from modules.watchlist import remove_watch

    success = remove_watch(ts_code)
    return {"status": "ok" if success else "not_found", "ts_code": ts_code}


@mcp.tool()
def scan_watchlist() -> dict[str, Any]:
    """
    扫描自选股，检测 B1/B2/B3、出货信号、异动等。

    Returns:
        扫描结果汇总 + 每只股票的警报列表
    """
    from modules.watchlist import scan_watchlist

    result = scan_watchlist()

    alerts = []
    for a in result.get("alerts", []):
        if hasattr(a, "ts_code"):
            alerts.append({
                "ts_code": a.ts_code,
                "name": a.name,
                "alert_type": a.alert_type,
                "level": a.level,
                "message": a.message,
            })
        elif isinstance(a, dict):
            alerts.append(a)

    summary = result.get("summary", {})
    return {
        "total": summary.get("total", 0),
        "b1_count": summary.get("b1_count", 0),
        "b2_count": summary.get("b2_count", 0),
        "exit_count": summary.get("exit_count", 0),
        "break_count": summary.get("break_count", 0),
        "abnormal_count": summary.get("abnormal_count", 0),
        "alerts": alerts,
    }


@mcp.tool()
def generate_daily_report() -> dict[str, Any]:
    """
    生成自选股日报（Z哥风格）。

    Returns:
        日报文本
    """
    from modules.watchlist import generate_daily_report

    report_text = generate_daily_report()
    return {"report": report_text}


# =============================================================================
# 持仓诊断工具
# =============================================================================


@mcp.tool()
def diagnose_stock(ts_code: str, days: int = 120) -> dict[str, Any]:
    """
    对单只股票进行完整持仓诊断。

    检查项包括：
      - KDJ J 值、MACD 一票否决
      - BBI/白线/黄线位置
      - 金叉 / 死叉
      - 防卖飞评分（0-100）
      - 出货信号
      - 买入信号（B1/B2/B3）
      - 麒麟会阶段
      - 蜈蚣 / 铁蝴蝶 / 沙漏形态
      - 止损位 / 目标价

    Args:
        ts_code: 股票代码（如 600519.SH）
        days: 回溯天数（默认 120）

    Returns:
        完整诊断结果字典
    """
    from modules.portfolio_diagnosis import diagnose_stock as _diagnose

    report = _diagnose(ts_code, days=days)

    # 序列化出货信号
    exit_signals = []
    for sig in getattr(report, "exit_signals", []):
        if isinstance(sig, dict):
            exit_signals.append(sig)
        elif hasattr(sig, "signal_type"):
            exit_signals.append({
                "signal_type": sig.signal_type,
                "date": getattr(sig, "date", ""),
                "description": getattr(sig, "description", ""),
                "confidence": getattr(sig, "confidence", 0),
            })

    # 序列化买入信号
    buy_signals = []
    for sig in getattr(report, "buy_signals", []):
        if isinstance(sig, dict):
            buy_signals.append(sig)
        elif hasattr(sig, "strategy"):
            buy_signals.append({
                "signal_type": sig.strategy.value if hasattr(sig.strategy, "value") else str(sig.strategy),
                "date": sig.trade_date,
                "description": sig.description,
                "confidence": sig.confidence,
                "action": sig.action,
            })

    return {
        "ts_code": ts_code,
        "name": getattr(report, "name", ts_code),
        "price": getattr(report, "price", 0),
        "trade_date": getattr(report, "trade_date", ""),
        "price_position": getattr(report, "price_position", ""),
        "trend_status": getattr(report, "trend_status", ""),
        "kdj_j": getattr(report, "kdj_j", 0),
        "macd_dif": getattr(report, "macd_dif", 0),
        "macd_veto": getattr(report, "macd_veto", False),
        "bbi": getattr(report, "bbi", 0),
        "white_line": getattr(report, "white_line", 0),
        "yellow_line": getattr(report, "yellow_line", 0),
        "is_gold_cross": getattr(report, "is_gold_cross", False),
        "is_dead_cross": getattr(report, "is_dead_cross", False),
        "sell_score": getattr(report, "sell_score", 0),
        "sell_score_desc": getattr(report, "sell_score_desc", ""),
        "sell_score_details": getattr(report, "sell_score_details", {}),
        "exit_signals": exit_signals,
        "buy_signals": buy_signals,
        "kirin_phase": getattr(report, "kirin_phase", "UNKNOWN"),
        "kirin_confidence": getattr(report, "kirin_confidence", 0),
        "is_centipede": getattr(report, "is_centipede", False),
        "centipede_score": getattr(report, "centipede_score", 0),
        "bull_rope_status": getattr(report, "bull_rope_status", ""),
        "bull_rope_gap_pct": getattr(report, "bull_rope_gap_pct", 0),
        "sandglass_score": getattr(report, "sandglass_score", 0),
        "sandglass_is_perfect": getattr(report, "sandglass_is_perfect", False),
        "stop_loss": getattr(report, "stop_loss", None),
        "target_price": getattr(report, "target_price", None),
        "recommendation": getattr(report, "recommendation", ""),
        "risk_level": getattr(report, "risk_level", "UNKNOWN"),
    }


# =============================================================================
# 选股筛选工具
# =============================================================================


STRATEGY_ALIAS = {
    "B1": "b1",
    "B2": "b2_breakout",
    "B3": "b3_consensus",
    "完美图形": "perfect",
    "超级B1": "super_b1",
    "长安战法": "changan",
    "建仓波": "build_wave",
    "吸筹": "xishou",
    "安全": "safe",
    "超跌": "oversold",
    "突破": "breakout",
}

STRATEGY_DESCRIPTIONS = {
    "B1": "B1 买点 — J 值超卖 + 缩量回调至 BBI 附近",
    "B2": "B2 确认 — B1 后放量长阳突破",
    "B3": "B3 共识 — B2 后小阳线确认",
    "完美图形": "完美图形 — BBI 之上 + 缩量整理 + 均线多头",
    "超级B1": "超级 B1 — 多条件叠加的极强 B1",
    "长安战法": "长安战法 — B1 + 放量长阳 + 缩量分歧转一致",
    "建仓波": "建仓波 — 三波理论中的建仓阶段",
    "吸筹": "吸筹 — 麒麟会吸筹阶段特征",
    "安全": "安全 — 低风险综合筛选",
    "超跌": "超跌 — RSI/WR 超卖 + 偏离均线",
    "突破": "突破 — 放量突破关键阻力位",
}


@mcp.tool()
def get_screen_strategies() -> dict[str, Any]:
    """
    列出所有可用的选股策略及其说明。

    Returns:
        策略列表，包含 alias / criteria / description
    """
    strategies = []
    for alias, criteria in STRATEGY_ALIAS.items():
        strategies.append({
            "alias": alias,
            "criteria": criteria,
            "description": STRATEGY_DESCRIPTIONS.get(alias, ""),
        })
    return {"strategies": strategies}


@mcp.tool()
def run_screen(strategy: str, limit: int = 20) -> dict[str, Any]:
    """
    执行选股筛选。

    Args:
        strategy: 策略名称（B1/B2/B3/完美图形/长安战法/超跌/突破 等）
        limit: 返回数量上限（默认 20）

    Returns:
        选股结果，每只股票包含评分、评级、理由、警告
    """
    from modules.screener import screen_stocks

    # 支持中文别名
    criteria = STRATEGY_ALIAS.get(strategy, strategy.lower())

    scores = screen_stocks(
        criteria=criteria,
        max_stocks=limit,
        use_parallel=True,
    )

    stocks = []
    for s in scores[:limit]:
        stocks.append({
            "ts_code": s.ts_code,
            "name": s.name,
            "score": round(s.score, 1),
            "b1_score": round(s.b1_score, 1),
            "trend_score": round(s.trend_score, 1),
            "volume_score": round(s.volume_score, 1),
            "risk_score": round(s.risk_score, 1),
            "rating": s.rating,
            "reasons": s.reasons,
            "warnings": s.warnings,
        })

    return {
        "strategy": strategy,
        "criteria": criteria,
        "count": len(stocks),
        "stocks": stocks,
    }


# =============================================================================
# 系统工具
# =============================================================================


@mcp.tool()
def get_system_status() -> dict[str, Any]:
    """
    获取 MCP 服务器系统状态。

    Returns:
        包含数据模式、数据库路径、版本号等信息
    """
    from modules import get_data_mode, get_db_path, get_project_root
    from modules.database import get_connection

    db_path = get_db_path()
    data_mode = get_data_mode()
    project_root = get_project_root()

    # 统计数据库中的数据量
    db_stats = {}
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            for table in ["stock_basic", "daily_kline", "trade_records", "watchlist"]:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                db_stats[table] = cursor.fetchone()[0]
    except Exception as e:
        db_stats["error"] = str(e)

    return {
        "name": "investment-ledger-mcp",
        "version": "1.0.0",
        "data_mode": data_mode,
        "db_path": str(db_path),
        "project_root": str(project_root),
        "database_stats": db_stats,
    }


# =============================================================================
# 主入口
# =============================================================================


def main():
    """CLI 入口 — stdio 模式运行 MCP 服务器"""
    logger.info("=" * 50)
    logger.info("Z哥投资账本 MCP Server 启动")
    logger.info("=" * 50)

    try:
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error("MCP 服务器异常退出: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
