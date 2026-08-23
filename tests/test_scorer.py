"""Tests for trading score (60% real + 40% LLM stub)."""

import pytest

from modules.self_optimizer.scorer import (
    compute_total_score,
    compute_trading_score,
)


@pytest.fixture
def good_monthly_stats():
    """胜率 8%, 回撤 8%, 准确率 60% → 应得高分."""
    return {
        "avg_return": 8.0,
        "avg_drawdown": 8.0,
        "accuracy_rate": 60.0,
        "stock_count": 20,
    }


@pytest.fixture
def bad_monthly_stats():
    """胜率 -15%, 回撤 35%, 准确率 20% → 应得低分."""
    return {
        "avg_return": -15.0,
        "avg_drawdown": 35.0,
        "accuracy_rate": 20.0,
        "stock_count": 15,
    }


@pytest.fixture
def extreme_values():
    """极端值: 胜率 +50%, 回撤 0%, 准确率 100% → 必须 clamp."""
    return {
        "avg_return": 50.0,
        "avg_drawdown": 0.0,
        "accuracy_rate": 100.0,
        "stock_count": 30,
    }


def test_trading_score_good(good_monthly_stats):
    score = compute_trading_score(good_monthly_stats)
    # 18 (胜率 8% → 8/10 * 30 = 24)
    # 18 (回撤 8% → 满分 30, 因为 <10% 满分)
    # 24 (准确率 60% → 60/100 * 40 = 24)
    # 总: 24 + 30 + 24 = 78, 但 cap 60
    assert 55 <= score <= 60


def test_trading_score_bad(bad_monthly_stats):
    score = compute_trading_score(bad_monthly_stats)
    # 胜率 -15% → clamp -10% 映射 0 分
    # 回撤 35% → 10-50% 线性 0-30, 35% → (50-35)/40*30 = 11.25
    # 准确率 20% → 20/100 * 40 = 8
    # 总: 0 + 11.25 + 8 = 19.25
    assert 15 <= score <= 25


def test_trading_score_clamping(extreme_values):
    score = compute_trading_score(extreme_values)
    # clamp 胜率 +50% → +10% → 30 分
    # 回撤 0% → 满分 30
    # 准确率 100% → 40 分
    # 总: 30 + 30 + 40 = 100, 但 cap 60
    assert score == 60


def test_total_score_combines_real_and_llm(good_monthly_stats, monkeypatch):
    """验证 60% 真实 + 40% LLM 加总公式."""
    # monkeypatch LLM 调用避免真打 API
    from modules.self_optimizer import scorer

    monkeypatch.setattr(scorer, "compute_llm_score", lambda proposed: 30.0)
    total, breakdown = compute_total_score("2026-05", good_monthly_stats, proposed={})
    # 60 分真实 + 30 分 LLM = 90
    assert 85 <= total <= 95
    assert breakdown["real"] > 0
    assert breakdown["llm"] == 30.0
