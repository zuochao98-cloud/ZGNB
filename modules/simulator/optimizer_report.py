#!/usr/bin/env python3
"""
Walk-forward 参数寻优报告输出。

提供文本和 JSON 格式的报告生成。
"""

from __future__ import annotations

from typing import Any
from dataclasses import asdict

from .walk_forward import WalkForwardResult


def summary_text(result: WalkForwardResult) -> str:
    """格式化 walk-forward 结果为可读文本。"""
    lines = [
        f"{'=' * 60}",
        "Walk-forward 参数寻优结果",
        f"{'=' * 60}",
        f"窗口数:       {len(result.windows)}",
        f"训练天数:     {result.config.train_days}",
        f"验证天数:     {result.config.test_days}",
        f"目标函数:     {result.config.objective}",
        f"过拟合比率:   {result.overfit_ratio:.2f} (接近 1 表示不过拟合)",
        f"{'=' * 60}",
        "",
        "OOS 统计指标:",
        f"  年化收益:   {result.oos_metrics.annualized_return:+.2%}",
        f"  夏普比率:   {result.oos_metrics.sharpe_ratio:.2f}",
        f"  Calmar:     {result.oos_metrics.calmar_ratio:.2f}",
        f"  最大回撤:   {result.oos_metrics.max_drawdown:.2%}",
        f"  胜率:       {result.oos_metrics.win_rate:.1%}",
        "",
        "各窗口最佳参数:",
    ]

    for w in result.windows:
        lines.append(f"  窗口 {w.window_index}: IS={w.is_score:.2f}, OOS={w.oos_score:.2f}")
        for k, v in w.best_params.items():
            lines.append(f"    {k} = {v}")

    lines.append(f"{'=' * 60}")
    return "\n".join(lines)


def to_dict(result: WalkForwardResult) -> dict[str, Any]:
    """将 WalkForwardResult 转换为可序列化的字典。"""
    return {
        "config": {
            "train_days": result.config.train_days,
            "test_days": result.config.test_days,
            "objective": result.config.objective,
            "anchored": result.config.anchored,
        },
        "windows": [
            {
                "window_index": w.window_index,
                "is_start": w.is_start,
                "is_end": w.is_end,
                "oos_start": w.oos_start,
                "oos_end": w.oos_end,
                "best_params": w.best_params,
                "is_score": w.is_score,
                "oos_score": w.oos_score,
            }
            for w in result.windows
        ],
        "oos_equity_curve": result.oos_equity_curve,
        "oos_metrics": asdict(result.oos_metrics),
        "overfit_ratio": result.overfit_ratio,
    }
