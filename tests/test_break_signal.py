"""Tests for break signal (连续 2 轮 Δ<2 → stop)."""

from modules.self_optimizer.phase2_hillclimb import (
    RoundResult,
    check_break_signal,
)


def _make_result(delta: float, status: str = "revert") -> RoundResult:
    return RoundResult(
        round=1,
        old_score=80.0,
        new_score=80.0 + delta,
        delta=delta,
        status=status,
        violations=[],
        proposed_diff="",
        timestamp="2026-06-11T00:00:00",
    )


def test_two_consecutive_small_delta_breaks():
    """连续 2 轮 Δ<2 → break."""
    history = [_make_result(1.5), _make_result(1.0)]
    assert check_break_signal(history, threshold=2.0) is True


def test_one_small_one_large_does_not_break():
    """一 Δ<2 + 一 Δ>=2 → 不 break."""
    history = [_make_result(1.5), _make_result(2.5)]
    assert check_break_signal(history, threshold=2.0) is False


def test_empty_history_does_not_break():
    assert check_break_signal([]) is False


def test_single_round_does_not_break():
    history = [_make_result(0.5)]
    assert check_break_signal(history) is False
