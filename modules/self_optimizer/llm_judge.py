"""LLM judge with paired within-judge (PR #13 教训).

V1 stub: 返回固定值. V1.1+ 接 modules/llm_providers.py.
"""

from __future__ import annotations

from typing import Any


def paired_judge(
    before: str,
    after: str,
    prompt_template: str = "",
) -> bool:
    """1 轮 paired within-judge.

    V1 stub: 总是 True (after 更好). V1.1+ 接真 LLM.
    必须 paired (同 call 给 before+after), 禁止单边.
    """
    return True


def compute_llm_score_with_baseline(
    baseline: dict[str, Any],
    new: dict[str, Any],
) -> float:
    """返回 0-40. V1 stub: 20."""
    return 20.0
