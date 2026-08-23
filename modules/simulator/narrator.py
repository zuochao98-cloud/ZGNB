#!/usr/bin/env python3
"""
模拟器 Z哥风格叙事生成器（v3.6.0 新增）

把 SimulationResult 序列化为可读提示词，调用 LLM 生成 Z哥风格的点评。
模式模仿 commentary_service.py，但场景从「单股分析」迁移到「组合模拟回测」。
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from . import SimulationResult

logger = logging.getLogger(__name__)

# ── 缓存 ──

_cache: dict[str, tuple[dict[str, Any], float]] = {}
_CACHE_TTL = int(os.getenv("SIMULATION_NARRATE_CACHE_TTL", "3600"))
_CACHE_MAX = 100

_skill_cache: str | None = None
_skill_mtime: float = 0

_KNOWLEDGE_DIR = Path(__file__).parent.parent.parent / "knowledge"
_SKILL_PATH = Path(__file__).parent.parent.parent / "SKILL.md"

_TARGET_SECTIONS = [
    "## 角色扮演规则（最重要）",
    "## 身份卡",
    "## 表达 DNA",
    "## 决策启发式",
    "## 价值观与反模式",
    "## 诚实边界",
]


# ── 黑话词典（从 trade_reviewer 复用，import 失败时回落到空 dict）──

try:
    from modules.trade_reviewer import JARGON_DICT
except ImportError:  # pragma: no cover
    JARGON_DICT = {}


SIMULATION_NARRATIVE_PROMPT = """你以 zettaranc（Z哥）的身份点评用户的端到端模拟回测结果。

**用户的故事是**：把一笔钱交给系统，按 A 股真实约束（T+1、涨跌停、停牌）+ 真实成本（佣金、印花税、过户费）+ 动态滑点 + ATR 仓位 + 战法共振过滤跑了一遍，看系统怎么表现。

**风格要求**：
- 直接、犀利、不废话
- 常用反问句确认用户理解
- 结尾用金句收尾
- 可以用黑话：卤煮=落袋为安、建仓=试探仓位、卖飞=卖出后大涨、搬砖=无效交易
- 参考语料库中的表达方式

**点评维度**（不是买股卖股，是看一个作战小组能不能打）：
- 胜率：是否在合理范围，过高过低都要问为什么
- 最大回撤：能否扛住系统性回撤（10% 是黄牌，15% 是红牌，20%+ 是退场）
- 盈亏比：赔率够不够，吃的是大波段还是刀口舔血
- 策略适配性：战法共振、信号频率、信号质量
- 风险敞口：单票最大仓位、最大连亏、最大持仓天数是否合理

**输出结构**：
1. **开盘定性**（一句话概括这是赚钱的故事还是亏钱的故事）
2. **战绩解读**（看几组数字之间的关系，不是念数字）
3. **风险点评**（最怕的不是回撤，是扛不住的情绪化止损）
4. **策略适配性**（信号共振有没有起作用，频率够不够，太密集反而是噪声）
5. **操作建议**（给具体的调整方向：调仓、调阈值、调 ATR 窗口、调共振评分）
6. **Z哥金句**（一句收尾，要有你的风格）

**禁止**：
- 不要模板化输出
- 不要分点列表太多（超过 5 点）
- 不要用"首先...其次..."这种套路
- 不要逐个指标念数字，要说指标之间的关系
- 不要说"建议关注"这种废话
- 用「我」而非「Z哥认为」——你就是 Z哥，第一人称说

以上分析基于历史回测，不构成投资建议。
"""


def _load_skill_sections() -> str:
    """从 SKILL.md 提取点评相关的关键章节（mtime 缓存版）。"""
    global _skill_cache, _skill_mtime

    if not _SKILL_PATH.exists():
        return ""

    mtime = _SKILL_PATH.stat().st_mtime
    if _skill_cache and mtime == _skill_mtime:
        return _skill_cache

    lines = _SKILL_PATH.read_text(encoding="utf-8").split("\n")
    extracted: list[str] = []
    in_section = False

    for line in lines:
        if line.startswith("## "):
            header = line.strip()
            if header in _TARGET_SECTIONS:
                in_section = True
                extracted.append(f"\n{header}\n")
                continue
            if in_section:
                in_section = False

        if in_section and line.startswith("### "):
            extracted.append(f"\n{line}\n")
            continue

        if in_section:
            extracted.append(line)

    _skill_cache = "\n".join(extracted).strip()
    _skill_mtime = mtime
    return _skill_cache


def _read_section_text(filepath: str, max_bytes: int = 600) -> str:
    """读知识库文件前 N 字节作为片段（防止 prompt 爆炸）。"""
    path = _KNOWLEDGE_DIR / filepath
    if not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("读取知识库失败 %s: %s", filepath, exc)
        return ""
    if len(text.encode("utf-8")) > max_bytes:
        return text[:max_bytes] + "\n...(截断)"
    return text.strip()


def _load_knowledge_snippets(result: SimulationResult) -> str:
    """
    模拟器视角的条件知识注入：
    - 回撤 > 15% → 逃顶规则
    - 交易 > 50 → 仓位管理
    - 胜率 < 35% → 卖出纪律
    - 平均持仓 < 3 天 → 短线核心
    - 始终注入 JARGON_DICT
    """
    snippets: list[str] = []

    if result.max_drawdown > 0.15:
        s = _read_section_text("exit-strategies.md", max_bytes=800)
        if s:
            snippets.append(f"【逃顶/回撤规则】\n{s}")

    if result.total_trades > 50:
        s = _read_section_text("position-management.md", max_bytes=800)
        if s:
            snippets.append(f"【仓位管理】\n{s}")

    if result.win_rate < 0.35:
        s = _read_section_text("sell-discipline.md", max_bytes=600)
        if s:
            snippets.append(f"【卖出纪律】\n{s}")

    if result.avg_holding_days < 3:
        s = _read_section_text("trading-core.md", max_bytes=600)
        if s:
            snippets.append(f"【短线核心】\n{s}")

    if JARGON_DICT:
        jargon_lines = "\n".join(f"- {k}: {v}" for k, v in list(JARGON_DICT.items())[:10])
        snippets.append(f"【黑话词典】\n{jargon_lines}")

    return "\n\n".join(snippets)


def _serialize_result(result: SimulationResult) -> dict[str, Any]:
    """稳定字段子集——只保留影响叙事的 key，避免无关字段污染缓存命中。"""
    config = result.config
    metrics_obj = result.metrics
    metrics_dict: dict[str, Any] = {}
    if metrics_obj is not None and hasattr(metrics_obj, "__dict__"):
        metrics_dict = dict(metrics_obj.__dict__)
    elif isinstance(metrics_obj, dict):
        metrics_dict = metrics_obj

    return {
        "ts_codes": sorted({t.ts_code for t in result.trades}),
        "initial_capital": result.initial_capital,
        "final_value": result.final_value,
        "total_return": result.total_return,
        "max_drawdown": result.max_drawdown,
        "sharpe_ratio": result.sharpe_ratio,
        "win_rate": result.win_rate,
        "profit_factor": result.profit_factor,
        "total_trades": result.total_trades,
        "avg_holding_days": result.avg_holding_days,
        "metrics_signature": {
            "annualized_return": metrics_dict.get("annualized_return"),
            "calmar_ratio": metrics_dict.get("calmar_ratio"),
            "sortino_ratio": metrics_dict.get("sortino_ratio"),
            "alpha": metrics_dict.get("alpha"),
            "beta": metrics_dict.get("beta"),
            "volatility_annual": metrics_dict.get("volatility_annual"),
        },
        "config_signature": {
            "max_positions": getattr(config, "max_positions", None),
            "use_atr_sizing": getattr(config, "use_atr_sizing", None),
            "max_position_pct": getattr(config, "max_position_pct", None),
            "strategy_mode": getattr(config, "strategy_mode", None),
        },
        "n_trades": len(result.trades),
    }


def _get_cache_key(result: SimulationResult) -> str:
    """稳定字段 JSON + sha256 当 cache key——不同输入一定不同 key。"""
    blob = json.dumps(_serialize_result(result), sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _build_user_prompt(result: SimulationResult) -> str:
    """SimulationResult → 人类可读摘要（600-900 字点评的目标输入）。"""
    config = result.config
    metrics = result.metrics
    ts_codes = sorted({t.ts_code for t in result.trades}) or ["(未成交)"]

    sections: list[str] = [
        "请基于以下端到端模拟结果生成 Z哥风格的点评：",
        "",
        "【总体战绩】",
        f"- 标的池: {' / '.join(ts_codes[:10])}{' 等' if len(ts_codes) > 10 else ''} (共 {len(ts_codes)} 只)",
        f"- 初始资金: ¥{result.initial_capital:,.0f}",
        f"- 期末净值: ¥{result.final_value:,.0f}",
        f"- 总收益: {result.total_return * 100:+.2f}%",
        f"- 总交易: {result.total_trades} 笔",
        f"- 平均持仓: {result.avg_holding_days:.1f} 天",
        "",
        "【胜率盈亏】",
        f"- 胜率: {result.win_rate * 100:.1f}%",
        f"- 盈亏比: {result.profit_factor:.2f}",
        f"- 夏普比率: {result.sharpe_ratio:.2f}",
    ]

    if metrics is not None and hasattr(metrics, "annualized_return"):
        try:
            sections.extend(
                [
                    f"- 年化收益: {metrics.annualized_return * 100:+.2f}%",
                    f"- Calmar: {metrics.calmar_ratio:.2f}",
                    f"- 索提诺: {metrics.sortino_ratio:.2f}",
                    f"- 波动率: {metrics.volatility_annual * 100:.2f}%",
                    f"- 最大连胜/连亏: {metrics.max_consecutive_wins} / {metrics.max_consecutive_losses}",
                ]
            )
        except AttributeError:
            pass

    sections.extend(
        [
            "",
            "【风险敞口】",
            f"- 最大回撤: {result.max_drawdown * 100:.2f}%",
            f"- 单笔风险: {config.risk_per_trade * 100:.2f}%",
            f"- 单票最大仓位: {getattr(config, 'max_position_pct', 0.0) * 100:.2f}%",
            f"- 最大同时持仓: {getattr(config, 'max_positions', 0)}",
            f"- 现金利用率上限: {getattr(config, 'cash_utilization_limit', 0.0) * 100:.0f}%",
            "",
            "【市场环境与基准】",
            f"- 基准: {getattr(config, 'benchmark_code', 'N/A')}",
            f"- 成本模型: {type(config.cost_model).__name__}",
            f"- 滑点模型: {type(config.slippage_model).__name__}",
            f"- 动态滑点: {getattr(config, 'use_dynamic_slippage', False)}",
            f"- ATR 仓位: {getattr(config, 'use_atr_sizing', False)}",
        ]
    )

    resonance = result.resonance_summary or {}
    if resonance:
        sections.extend(
            [
                "",
                "【战法共振】",
                f"- 模式: {resonance.get('mode', 'simple')}",
                f"- 信号总数: {resonance.get('total_signals_evaluated', 0)}",
                f"- 触发战法: {', '.join(resonance.get('matched_strategies', []) or ['无'])}",
                f"- 冲突标签: {', '.join(resonance.get('conflicts', []) or ['无'])}",
                f"- 平均买入分: {resonance.get('avg_buy_score', 0):.2f}",
                f"- 平均风险分: {resonance.get('avg_risk_score', 0):.2f}",
            ]
        )

    if result.positions:
        sections.extend(["", f"【仍未平仓 {len(result.positions)} 只】"])
        for pos in result.positions[:5]:
            sections.append(f"- {pos.ts_code} {pos.name} | 进场 {pos.entry_date} @ {pos.entry_price:.2f}")

    if result.trades:
        recent_sells = [t for t in result.trades if getattr(t, "action", "") == "SELL"][-5:]
        if recent_sells:
            sections.extend(["", "【最近 5 笔平仓】"])
            for t in recent_sells:
                try:
                    sections.append(
                        f"- {t.date} {t.ts_code} {t.action} @ {t.price:.2f} 盈亏 {t.pnl_pct * 100:+.2f}% ({t.reason})"
                    )
                except AttributeError:
                    continue

    sections.extend(
        [
            "",
            "请按以下结构输出（600-900 字）：",
            "",
            "1. **开盘定性**（一句话点出赚钱/亏钱 + 状态判断）",
            "2. **战绩解读**（看指标间的关系，不是念数字）",
            "3. **风险点评**（回撤能扛住吗？止损规则在生效吗？）",
            "4. **策略适配性**（信号频率够不够？战法共振是有效还是噪声？）",
            "5. **操作建议**（给具体的调参方向）",
            "6. **Z哥金句**（一句收尾）",
            "",
            "注意：不要逐个念数据，说关系；不要使用 markdown 标题，用加粗；用你的风格。",
        ]
    )

    return "\n".join(sections)


def _fallback_text(reason: str) -> str:
    """LLM 未配置时返回的简短提示 + Z哥风格兜底话术。"""
    return (
        f"[LLM 未配置] {reason}\n\n"
        "你跑了一次端到端模拟，先看三个数字：胜率、最大回撤、盈亏比。\n"
        "它们仨讲故事比你自己讲得清楚。\n"
        "兄弟，等模型就位再让我评。"
    )


def generate_simulation_narrative(result: SimulationResult) -> dict[str, Any]:
    """
    生成模拟结果 Z哥风格叙事点评。

    Returns:
        {simulation_id, ts_codes, days, narrative_text, generated_at, model_used, cached, error?}
    """
    cache_key = _get_cache_key(result)
    ts_codes = sorted({t.ts_code for t in result.trades})
    days = len(result.equity_curve) if result.equity_curve else 0

    # ── 缓存命中 ──
    if cache_key in _cache:
        cached_payload, ts = _cache[cache_key]
        if time.time() - ts < _CACHE_TTL:
            payload = dict(cached_payload)
            payload["cached"] = True
            payload["simulation_id"] = cache_key
            payload["ts_codes"] = ts_codes
            payload["days"] = days
            return payload

    # ── 准备提示词 ──
    system_prompt = _load_skill_sections()
    user_prompt = _build_user_prompt(result)

    knowledge = _load_knowledge_snippets(result)
    if knowledge:
        user_prompt += f"\n\n【参考知识库】\n{knowledge}"

    model_name = os.getenv("LLM_MODEL", "MiniMax-M3")

    def _log_response(success: bool, elapsed_ms: float, error_message: str = "") -> None:
        try:
            from modules.database import record_llm_response

            record_llm_response(
                ts_code="SIMULATION",
                model=model_name,
                response_time_ms=elapsed_ms,
                success=success,
                error_message=error_message,
            )
        except (ImportError, AttributeError, sqlite3.Error):
            logger.debug("record_llm_response 调用失败（忽略）", exc_info=True)

    # ── 调用 LLM ──
    start_ts = time.perf_counter()
    try:
        from modules.llm_providers import MiniMaxProvider

        provider = MiniMaxProvider()
        text = provider.generate(system_prompt, user_prompt, temperature=0.7)
        elapsed_ms = (time.perf_counter() - start_ts) * 1000.0

        text = re.sub(r"think.*?think", "", text, flags=re.DOTALL).strip()
        _log_response(success=True, elapsed_ms=elapsed_ms)

    except ValueError as exc:
        elapsed_ms = (time.perf_counter() - start_ts) * 1000.0
        logger.warning("LLM 未配置，使用 fallback: %s", exc)
        _log_response(success=False, elapsed_ms=elapsed_ms, error_message=str(exc))
        return {
            "simulation_id": cache_key,
            "ts_codes": ts_codes,
            "days": days,
            "narrative_text": _fallback_text(str(exc)),
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model_used": "",
            "cached": False,
            "error": "llm_not_configured",
        }

    except (ConnectionError, TimeoutError, RuntimeError, OSError, ValueError) as exc:
        elapsed_ms = (time.perf_counter() - start_ts) * 1000.0
        logger.error("LLM 生成失败: %s", exc, exc_info=True)
        _log_response(success=False, elapsed_ms=elapsed_ms, error_message=str(exc))
        return {
            "simulation_id": cache_key,
            "ts_codes": ts_codes,
            "days": days,
            "narrative_text": f"[生成失败] {exc}",
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model_used": os.getenv("LLM_MODEL", ""),
            "cached": False,
            "error": "llm_failed",
        }

    # ── 写入缓存 ──
    payload = {
        "simulation_id": cache_key,
        "ts_codes": ts_codes,
        "days": days,
        "narrative_text": text,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model_used": os.getenv("LLM_MODEL", "MiniMax-M3"),
        "cached": False,
    }

    if len(_cache) >= _CACHE_MAX:
        oldest_key = min(_cache, key=lambda k: _cache[k][1])
        del _cache[oldest_key]
    _cache[cache_key] = (payload, time.time())

    return payload


__all__ = [
    "SIMULATION_NARRATIVE_PROMPT",
    "_load_skill_sections",
    "_load_knowledge_snippets",
    "_build_user_prompt",
    "_serialize_result",
    "_get_cache_key",
    "generate_simulation_narrative",
]
