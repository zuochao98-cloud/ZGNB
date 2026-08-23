"""Trading reflex blacklist (8 anti-patterns from real trading pitfalls).

每个反例来自 zettaranc-skill 现有 harness_updater.py 逻辑 + 推断的踩坑场景.
任何触发强制 status=revert, 防止自我优化引入回归.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from modules.core.errors import ErrorCode

logger = logging.getLogger(__name__)


@dataclass
class Violation:
    """单条反例违规."""

    name: str
    description: str
    detail: str = ""


# 8 条反例检测函数


def _check_high_return_no_warning(ctx: dict) -> list[Violation]:
    proposed = ctx.get("proposed", [])
    violations = []
    for item in proposed:
        if item.get("status") == "good" and item.get("avg_return", 0) < -10:
            violations.append(
                Violation(
                    name="high_return_no_warning",
                    description="胜率<-10% 仍标为 good 状态",
                    detail=f"strategy={item.get('strategy')}, avg_return={item.get('avg_return')}",
                )
            )
    return violations


def _check_low_sample_size(ctx: dict) -> list[Violation]:
    analysis = ctx.get("analysis", {})
    stats = analysis.get("strategy_stats", []) if isinstance(analysis, dict) else []
    violations = []
    for stat in stats:
        if stat.get("stock_count", 0) < 5:
            violations.append(
                Violation(
                    name="low_sample_size",
                    description="stock_count<5 强行评估",
                    detail=f"strategy_tags={stat.get('strategy_tags')}, stock_count={stat.get('stock_count')}",
                )
            )
    return violations


def _check_high_drawdown_no_limit(ctx: dict) -> list[Violation]:
    proposed = ctx.get("proposed", [])
    violations = []
    for item in proposed:
        if item.get("avg_drawdown", 0) > 20 and item.get("status") != "risky":
            violations.append(
                Violation(
                    name="high_drawdown_no_limit",
                    description="回撤>20% 仍未标 risky",
                    detail=f"strategy={item.get('strategy')}, avg_drawdown={item.get('avg_drawdown')}, status={item.get('status')}",
                )
            )
    return violations


def _check_self_eval_context(ctx: dict) -> list[Violation]:
    llm_input = ctx.get("llm_input", {})
    if llm_input.get("contains_harness_output"):
        return [
            Violation(
                name="self_eval_context",
                description="LLM judge 读了 harness_updater 自己的输出 (PR #13 教训)",
                detail="judge 需用 paired within-judge, 不可用 harness 自身输出当 judge input",
            )
        ]
    return []


def _check_silent_exception(ctx: dict) -> list[Violation]:
    log = ctx.get("execution_log", [])
    violations = []
    for entry in log:
        if entry.get("status") == "failure" and not entry.get("raised", False):
            violations.append(
                Violation(
                    name="silent_exception",
                    description="异常被 swallow 而非 raise",
                    detail=f"action={entry.get('action')}, message={entry.get('message')}",
                )
            )
    return violations


def _check_multi_strategy_mutation(ctx: dict) -> list[Violation]:
    proposed = ctx.get("proposed", [])
    if len(proposed) > 2:
        return [
            Violation(
                name="multi_strategy_mutation",
                description="单轮提议改动 >2 个策略标签",
                detail=f"proposed count={len(proposed)}, max=2",
            )
        ]
    return []


def _check_dry_run_overload(ctx: dict) -> list[Violation]:
    history = ctx.get("history", [])
    if not history:
        return []
    dry_count = sum(1 for h in history if h.get("status") in ("dry_run", "revert"))
    ratio = dry_count / len(history)
    if ratio > 0.3:
        return [
            Violation(
                name="dry_run_overload",
                description="dry-run 比例 >30%",
                detail=f"ratio={ratio:.0%}, dry_count={dry_count}, total={len(history)}",
            )
        ]
    return []


def _check_ignore_real_signal(ctx: dict) -> list[Violation]:
    scoring = ctx.get("scoring", {})
    real_weight = scoring.get("real_weight", 0.0)
    if real_weight < 0.6:
        return [
            Violation(
                name="ignore_real_signal",
                description="只用 LLM judge 未充分参考 monthly_reviews_self",
                detail=f"real_weight={real_weight}, min=0.6",
            )
        ]
    return []


TRADING_BLACKLIST: list[tuple[str, str, Callable[[dict], list[Violation]]]] = [
    ("high_return_no_warning", "胜率<-10% 仍标 good", _check_high_return_no_warning),
    ("low_sample_size", "stock_count<5 强行评估", _check_low_sample_size),
    ("high_drawdown_no_limit", "回撤>20% 仍未标 risky", _check_high_drawdown_no_limit),
    ("self_eval_context", "LLM judge 读 harness 自身输出", _check_self_eval_context),
    ("silent_exception", "异常被 swallow 而非 raise", _check_silent_exception),
    ("multi_strategy_mutation", "单轮改 >2 个策略", _check_multi_strategy_mutation),
    ("dry_run_overload", "dry-run 比例 >30%", _check_dry_run_overload),
    ("ignore_real_signal", "real_weight<0.6", _check_ignore_real_signal),
]


def check_all(context: dict[str, Any]) -> list[Violation]:
    """运行所有 8 条反例, 返回所有触发的违规 (空列表 = 通过)."""
    violations: list[Violation] = []
    for name, description, check_fn in TRADING_BLACKLIST:
        try:
            violations.extend(check_fn(context))
        except (ValueError, KeyError, TypeError, AttributeError, IndexError) as e:
            logger.warning(
                "[reflex_blacklist] 黑名单检测异常 (code=%s, name=%s): %s",
                ErrorCode.REFLEX_BLACKLIST_FAILED.value,
                name,
                e,
            )
            violations.append(
                Violation(
                    name=name,
                    description=description,
                    detail=f"检测函数异常: {e}",
                )
            )
    return violations
