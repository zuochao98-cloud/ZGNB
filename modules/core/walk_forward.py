"""
Walk-forward 公共逻辑（v3.9.0 技术债务清理）

提取窗口切分的公共逻辑，供 simulator/walk_forward.py 和 verify/walk_forward.py 使用。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WalkForwardSplit:
    """Walk-forward 单段切片（按索引）"""

    train_start: int
    train_end: int
    test_start: int
    test_end: int


def make_walk_forward_splits(
    total_days: int,
    train_days: int,
    test_days: int,
    allow_partial_last: bool = True,
) -> list[WalkForwardSplit]:
    """
    生成 walk-forward 窗口切片。

    滚动窗口切分，步长 = test_days（让 OOS 段不重叠）：
      [IS: 0-120][OOS: 120-180]
      [IS: 60-180][OOS: 180-240]
      [IS: 120-240][OOS: 240-300]

    Args:
        total_days: 总天数
        train_days: 训练窗口天数
        test_days: 测试窗口天数
        allow_partial_last: 是否允许最后一段 OOS 部分覆盖（截断到 total_days）

    Returns:
        WalkForwardSplit 列表
    """
    splits: list[WalkForwardSplit] = []
    train_start = 0

    while True:
        train_end = train_start + train_days
        test_start = train_end
        test_end = test_start + test_days

        if test_start >= total_days:
            break

        # 允许最后一段 OOS 部分覆盖
        if allow_partial_last:
            effective_test_end = min(test_end, total_days)
        else:
            effective_test_end = test_end
            if effective_test_end > total_days:
                break

        splits.append(
            WalkForwardSplit(
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=effective_test_end,
            )
        )

        # 步长 = OOS 长度
        if test_end <= total_days:
            train_start += test_days
        else:
            break

    return splits


__all__ = [
    "WalkForwardSplit",
    "make_walk_forward_splits",
]
