"""Tests for trading reflex blacklist (8 anti-patterns)."""

import pytest

from modules.self_optimizer.reflex_blacklist import (
    TRADING_BLACKLIST,
    Violation,
    check_all,
)


# 8 个反例的 fixture


@pytest.fixture
def proposed_with_poor_strategy():
    """反例 #1: 胜率<-10% 仍被标为 good (与 status 一致性反)."""
    return {
        "proposed": [
            {"strategy": "波段", "status": "good", "avg_return": -15.0, "avg_drawdown": 10.0, "stock_count": 10}
        ]
    }


@pytest.fixture
def analysis_with_low_sample():
    """反例 #2: stock_count<5 强行评估."""
    return {
        "analysis": {
            "strategy_stats": [{"strategy_tags": "小盘", "stock_count": 3, "avg_return": 5.0, "avg_drawdown": 8.0}]
        }
    }


@pytest.fixture
def proposed_missing_drawdown_warning():
    """反例 #3: 回撤>20% 仍未标 risky."""
    return {
        "proposed": [
            {"strategy": "激进", "status": "good", "avg_return": 15.0, "avg_drawdown": 35.0, "stock_count": 10}
        ]
    }


@pytest.fixture
def llm_input_with_self_reference():
    """反例 #4: LLM judge 读了 harness_updater 自己的输出."""
    return {
        "llm_input": {
            "judge_prompt": "评估以下 harness_updater 输出: ...",
            "contains_harness_output": True,
        }
    }


@pytest.fixture
def execution_log_silent_exception():
    """反例 #5: 异常被 swallow 而非 raise."""
    return {
        "execution_log": [{"action": "analyze_strategy", "status": "failure", "raised": False, "message": "soft fail"}]
    }


@pytest.fixture
def proposed_multi_strategy_mutation():
    """反例 #6: 单轮提议改动 >2 个策略标签."""
    return {"proposed": [{"strategy": "A"}, {"strategy": "B"}, {"strategy": "C"}]}


@pytest.fixture
def history_high_dryrun():
    """反例 #7: dry-run 比例 >30%."""
    return {
        "history": [
            {"status": "dry_run"},
            {"status": "dry_run"},
            {"status": "dry_run"},
            {"status": "keep"},
        ]
    }


@pytest.fixture
def scoring_no_real_data():
    """反例 #8: 只用 LLM judge 未参考 monthly_reviews_self."""
    return {"scoring": {"real_weight": 0.0, "llm_weight": 1.0, "hard_rule_weight": 0.0}}


# 8 个单测


def test_high_return_no_warning(proposed_with_poor_strategy):
    violations = check_all(proposed_with_poor_strategy)
    assert any(v.name == "high_return_no_warning" for v in violations)


def test_low_sample_size(analysis_with_low_sample):
    violations = check_all(analysis_with_low_sample)
    assert any(v.name == "low_sample_size" for v in violations)


def test_high_drawdown_no_limit(proposed_missing_drawdown_warning):
    violations = check_all(proposed_missing_drawdown_warning)
    assert any(v.name == "high_drawdown_no_limit" for v in violations)


def test_self_eval_context(llm_input_with_self_reference):
    violations = check_all(llm_input_with_self_reference)
    assert any(v.name == "self_eval_context" for v in violations)


def test_silent_exception(execution_log_silent_exception):
    violations = check_all(execution_log_silent_exception)
    assert any(v.name == "silent_exception" for v in violations)


def test_multi_strategy_mutation(proposed_multi_strategy_mutation):
    violations = check_all(proposed_multi_strategy_mutation)
    assert any(v.name == "multi_strategy_mutation" for v in violations)


def test_dry_run_overload(history_high_dryrun):
    violations = check_all(history_high_dryrun)
    assert any(v.name == "dry_run_overload" for v in violations)


def test_ignore_real_signal(scoring_no_real_data):
    violations = check_all(scoring_no_real_data)
    assert any(v.name == "ignore_real_signal" for v in violations)


def test_blacklist_has_8_items():
    """结构性检查: 必须是 8 条."""
    assert len(TRADING_BLACKLIST) == 8


def test_check_all_returns_empty_when_clean():
    """通过的反例集应返回空列表."""
    clean_ctx = {
        "proposed": [{"strategy": "X", "status": "good", "avg_return": 12.0, "avg_drawdown": 8.0, "stock_count": 20}],
        "analysis": {
            "strategy_stats": [{"strategy_tags": "X", "stock_count": 20, "avg_return": 12.0, "avg_drawdown": 8.0}]
        },
        "llm_input": {"contains_harness_output": False},
        "execution_log": [{"status": "success", "raised": False}],
        "history": [{"status": "keep"}],
        "scoring": {"real_weight": 0.6, "llm_weight": 0.4, "hard_rule_weight": 0.0},
    }
    assert check_all(clean_ctx) == []
