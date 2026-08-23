"""
模拟器 Z哥风格叙事生成器测试（v3.6.0）

覆盖：
- _load_skill_sections() 能从 SKILL.md 提取关键章节
- _build_user_prompt() 把 SimulationResult 序列化为人类可读摘要
- _load_knowledge_snippets() 按指标条件注入知识片段
- _get_cache_key() 稳定 hash（同输入同输出）
- generate_simulation_narrative() LLM 成功 / 失败 / 缓存路径
- 不调用真实 LLM（统一用 patch）
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from modules.simulator import (
    CostModel,
    Position,
    SimulationConfig,
    SimulationResult,
    SlippageModel,
    TradeRecord,
)

# ── Fixtures ──


def _make_simulation_result(**overrides) -> SimulationResult:
    """构造一个最小可用的 SimulationResult。"""
    config = SimulationConfig(
        initial_capital=1_000_000.0,
        max_positions=overrides.get("max_positions", 5),
        risk_per_trade=overrides.get("risk_per_trade", 0.02),
        cost_model=CostModel(),
        slippage_model=SlippageModel(),
        use_atr_sizing=overrides.get("use_atr_sizing", False),
        max_position_pct=overrides.get("max_position_pct", 0.20),
        benchmark_code=overrides.get("benchmark_code", "000300.SH"),
        strategy_mode=overrides.get("strategy_mode", "simple"),
        min_resonance_score=overrides.get("min_resonance_score", 0.35),
    )

    trades = overrides.get("trades") or [
        TradeRecord(
            ts_code="600487.SH",
            name="亨通光电",
            action="BUY",
            date="20260115",
            price=22.50,
            shares=1000,
        ),
        TradeRecord(
            ts_code="600487.SH",
            name="亨通光电",
            action="SELL",
            date="20260122",
            price=24.10,
            shares=1000,
            pnl=1595.0,
            pnl_pct=0.0711,
            reason="卤煮：达到2R减半",
        ),
        TradeRecord(
            ts_code="000001.SZ",
            name="平安银行",
            action="BUY",
            date="20260201",
            price=10.20,
            shares=2000,
        ),
        TradeRecord(
            ts_code="000001.SZ",
            name="平安银行",
            action="SELL",
            date="20260210",
            price=9.80,
            shares=2000,
            pnl=-810.0,
            pnl_pct=-0.0392,
            reason="止损",
        ),
    ]

    positions = overrides.get("positions") or [
        Position(
            ts_code="600519.SH",
            name="贵州茅台",
            entry_date="20260301",
            entry_price=1680.0,
            shares=100,
            stop_loss=1600.0,
            take_profit=1800.0,
            risk_amount=8000.0,
            can_sell_date="20260302",
        )
    ]

    equity_curve = overrides.get("equity_curve") or [
        {"date": "20260101", "equity": 1_000_000.0},
        {"date": "20260201", "equity": 1_005_000.0},
        {"date": "20260301", "equity": 1_020_000.0},
    ]

    resonance = overrides.get("resonance_summary") or {
        "mode": "simple",
        "total_signals_evaluated": 8,
        "matched_strategies": ["B1"],
        "conflicts": [],
        "avg_buy_score": 0.65,
        "avg_risk_score": 0.10,
    }

    return SimulationResult(
        config=config,
        trades=trades,
        equity_curve=equity_curve,
        positions=positions,
        initial_capital=overrides.get("initial_capital", 1_000_000.0),
        final_value=overrides.get("final_value", 1_028_000.0),
        total_return=overrides.get("total_return", 0.028),
        max_drawdown=overrides.get("max_drawdown", 0.04),
        sharpe_ratio=overrides.get("sharpe_ratio", 1.2),
        win_rate=overrides.get("win_rate", 0.5),
        profit_factor=overrides.get("profit_factor", 1.8),
        total_trades=overrides.get("total_trades", 4),
        avg_holding_days=overrides.get("avg_holding_days", 5.0),
        resonance_summary=resonance,
    )


@pytest.fixture(autouse=True)
def reset_narrator_cache():
    """每个测试前后清 narrator 缓存，避免跨用例污染。"""
    from modules.simulator import narrator

    narrator._cache.clear()
    narrator._skill_cache = None
    narrator._skill_mtime = 0
    yield
    narrator._cache.clear()
    narrator._skill_cache = None
    narrator._skill_mtime = 0


# ── Tests ──


def test_load_skill_sections_returns_zg_role_rules():
    """_load_skill_sections 必须返回非空字符串、且含 Z哥角色相关章节。"""
    from modules.simulator import narrator

    text = narrator._load_skill_sections()
    assert isinstance(text, str)
    assert len(text) > 0
    # 至少包含一个角色扮演相关关键词
    assert any(kw in text for kw in ("角色", "Z哥", "DNA", "决策", "诚实", "启发"))


def test_build_user_prompt_contains_metrics():
    """prompt 必须包含 sharpe/win_rate/max_drawdown 三个核心数字。"""
    from modules.simulator import narrator

    result = _make_simulation_result()
    prompt = narrator._build_user_prompt(result)

    assert "夏普" in prompt or "Sharpe" in prompt or "1.20" in prompt
    assert "胜率" in prompt
    assert "最大回撤" in prompt
    # 显式包含数字
    assert "1.2" in prompt
    assert "50.0%" in prompt


def test_build_user_prompt_contains_trades_and_positions():
    """prompt 必须包含交易明细（ts_code + reason）和持仓明细（name）。"""
    from modules.simulator import narrator

    result = _make_simulation_result()
    prompt = narrator._build_user_prompt(result)

    assert "600487.SH" in prompt
    assert "000001.SZ" in prompt
    # reason 里的 Z哥风话术
    assert "卤煮" in prompt or "止损" in prompt
    # 持仓走 name 字段
    assert "贵州茅台" in prompt
    assert "仍未平仓" in prompt


def test_build_user_prompt_contains_resonance_when_present():
    """有战法共振数据时必须把数字注入。"""
    from modules.simulator import narrator

    result = _make_simulation_result(
        resonance_summary={
            "mode": "resonance",
            "total_signals_evaluated": 24,
            "matched_strategies": ["B1", "B2", "SB1"],
            "conflicts": ["三波冲刺"],
            "avg_buy_score": 0.72,
            "avg_risk_score": 0.18,
        }
    )
    prompt = narrator._build_user_prompt(result)

    assert "resonance" in prompt
    assert "24" in prompt
    assert "B1" in prompt
    assert "三波冲刺" in prompt


def test_load_knowledge_snippets_high_drawdown_injects_exit_rules():
    """max_drawdown > 0.15 时必须注入 exit-strategies 片段。"""
    from modules.simulator import narrator

    high_dd = _make_simulation_result(max_drawdown=0.20)
    snippets = narrator._load_knowledge_snippets(high_dd)
    assert "逃顶" in snippets
    assert "回撤" in snippets or "exit" in snippets.lower()


def test_load_knowledge_snippets_low_win_rate_injects_sell_discipline():
    """win_rate < 0.35 时必须注入 sell-discipline 片段。"""
    from modules.simulator import narrator

    low_wr = _make_simulation_result(win_rate=0.20)
    snippets = narrator._load_knowledge_snippets(low_wr)
    assert "卖出纪律" in snippets


def test_load_knowledge_snippets_high_trade_count_injects_position():
    """total_trades > 50 时必须注入 position-management 片段。"""
    from modules.simulator import narrator

    high_t = _make_simulation_result(total_trades=80)
    snippets = narrator._load_knowledge_snippets(high_t)
    assert "仓位管理" in snippets


def test_load_knowledge_snippets_low_holding_injects_core():
    """avg_holding_days < 3 时必须注入 trading-core 片段。"""
    from modules.simulator import narrator

    short_h = _make_simulation_result(avg_holding_days=1.5)
    snippets = narrator._load_knowledge_snippets(short_h)
    assert "短线核心" in snippets


def test_load_knowledge_snippets_no_signal_when_metrics_normal():
    """指标全部正常时不注入任何指标型知识（仍可能注入黑话）。"""
    from modules.simulator import narrator

    normal = _make_simulation_result(
        max_drawdown=0.05,
        win_rate=0.55,
        total_trades=20,
        avg_holding_days=5.0,
    )
    snippets = narrator._load_knowledge_snippets(normal)
    # 不应注入任何指标片段（黑话词典是恒注入，截断后单独算）
    assert "逃顶" not in snippets
    assert "卖出纪律" not in snippets
    assert "仓位管理" not in snippets
    assert "短线核心" not in snippets


def test_get_cache_key_stable_for_same_input():
    """同输入必须同 cache key。"""
    from modules.simulator import narrator

    a = _make_simulation_result()
    b = _make_simulation_result()
    assert narrator._get_cache_key(a) == narrator._get_cache_key(b)


def test_get_cache_key_differs_for_different_results():
    """不同输入必须不同 cache key。"""
    from modules.simulator import narrator

    a = _make_simulation_result(sharpe_ratio=1.2)
    b = _make_simulation_result(sharpe_ratio=2.5)
    assert narrator._get_cache_key(a) != narrator._get_cache_key(b)


def test_generate_narrative_success():
    """LLM 成功路径：返回的 dict 必含 8 个核心字段。"""
    from modules.llm_providers import MiniMaxProvider
    from modules.simulator import narrator

    result = _make_simulation_result()
    fake_text = "**开盘定性**赚钱了。\n\n**战绩解读**夏普 1.2，干得漂亮。\n\n**Z哥金句**赚钱不难，难的是一直赚。"

    with patch.object(MiniMaxProvider, "generate", return_value=fake_text):
        with patch.object(MiniMaxProvider, "__init__", return_value=None):
            out = narrator.generate_simulation_narrative(result)

    assert out["narrative_text"] == fake_text
    assert out["cached"] is False
    assert "simulation_id" in out and len(out["simulation_id"]) == 64
    assert "600487.SH" in out["ts_codes"]
    assert "000001.SZ" in out["ts_codes"]
    assert "model_used" in out
    assert "generated_at" in out
    assert "error" not in out or out.get("error") is None


def test_generate_narrative_cached_on_second_call():
    """第二次同输入必须返回 cached=True。"""
    from modules.llm_providers import MiniMaxProvider
    from modules.simulator import narrator

    result = _make_simulation_result()
    fake_text = "cached test 1.2 sharpe"

    with patch.object(MiniMaxProvider, "generate", return_value=fake_text) as mock_gen:
        with patch.object(MiniMaxProvider, "__init__", return_value=None):
            first = narrator.generate_simulation_narrative(result)
            second = narrator.generate_simulation_narrative(result)

    assert first["cached"] is False
    assert second["cached"] is True
    assert first["narrative_text"] == second["narrative_text"]
    assert mock_gen.call_count == 1


def test_generate_narrative_llm_not_configured():
    """LLM 未配置（ValueError）必须优雅降级。"""
    from modules.llm_providers import MiniMaxProvider
    from modules.simulator import narrator

    result = _make_simulation_result()

    def _raise_value_error(*args, **kwargs):
        raise ValueError("LLM_API_KEY not set. Please configure LLM_API_KEY in .env")

    with patch.object(MiniMaxProvider, "generate", side_effect=_raise_value_error):
        with patch.object(MiniMaxProvider, "__init__", return_value=None):
            out = narrator.generate_simulation_narrative(result)

    assert out.get("error") == "llm_not_configured"
    assert out["narrative_text"].startswith("[LLM 未配置]")
    assert out["cached"] is False
    assert out["model_used"] == ""


def test_generate_narrative_llm_generic_exception():
    """LLM 抛出非 ValueError 也必须优雅降级。"""
    from modules.llm_providers import MiniMaxProvider
    from modules.simulator import narrator

    result = _make_simulation_result()

    def _raise_runtime_error(*args, **kwargs):
        raise RuntimeError("network timeout")

    with patch.object(MiniMaxProvider, "generate", side_effect=_raise_runtime_error):
        with patch.object(MiniMaxProvider, "__init__", return_value=None):
            out = narrator.generate_simulation_narrative(result)

    assert out.get("error") == "llm_failed"
    assert "[生成失败]" in out["narrative_text"]
    assert "network timeout" in out["narrative_text"]


def test_generate_narrative_filters_think_tags():
    """LLM 输出含 think 区间时必须被剥离。"""
    from modules.llm_providers import MiniMaxProvider
    from modules.simulator import narrator

    result = _make_simulation_result()
    fake_text = "think 第一步推演 think **开盘定性**赚钱。"

    with patch.object(MiniMaxProvider, "generate", return_value=fake_text):
        with patch.object(MiniMaxProvider, "__init__", return_value=None):
            out = narrator.generate_simulation_narrative(result)

    assert "第一步推演" not in out["narrative_text"]
    assert "开盘定性" in out["narrative_text"]


def test_serialize_result_excludes_volatile_lists():
    """_serialize_result 必须只包含 stable 字段，不把每笔 trade 都序列化进缓存 key。"""
    from modules.simulator import narrator

    result = _make_simulation_result()
    payload = narrator._serialize_result(result)

    assert "ts_codes" in payload
    assert "total_return" in payload
    assert "metrics_signature" in payload
    assert "config_signature" in payload
    assert "trade_list" not in payload
    assert "positions" not in payload


def test_simulate_narrate_text_helper_in_cli_commands():
    """cli_commands 的 _simulate_narrate_text 在拿到 result 时应委派给 narrator。"""
    from modules.cli_commands import _simulate_narrate_text

    fake_out = {
        "simulation_id": "abc",
        "ts_codes": ["x"],
        "days": 1,
        "narrative_text": "ok",
        "generated_at": "",
        "model_used": "",
        "cached": False,
    }

    with patch("modules.simulator.narrator.generate_simulation_narrative", return_value=fake_out) as mock_gen:
        out = _simulate_narrate_text(result=object(), wf_payload=None)

    mock_gen.assert_called_once()
    assert out == fake_out


def test_simulate_narrate_text_helper_walk_forward_branch():
    """wf_payload 走『不调 LLM，直接出叙事』分支。"""
    from modules.cli_commands import _simulate_narrate_text

    wf_payload = {
        "config": {"train_days": 120, "test_days": 60, "objective": "calmar"},
        "windows": [{"window_index": 1}, {"window_index": 2}, {"window_index": 3}],
        "oos_metrics": {
            "annualized_return": 0.15,
            "sharpe_ratio": 1.4,
            "calmar_ratio": 1.2,
            "max_drawdown": 0.08,
        },
        "overfit_ratio": 0.85,
    }
    out = _simulate_narrate_text(result=None, wf_payload=wf_payload)

    assert out["simulation_id"] == "walk_forward"
    assert "120/60" in out["narrative_text"]
    assert "OOS 年化" in out["narrative_text"]
    assert "+15.00%" in out["narrative_text"]
    assert out["days"] == 180


def test_cli_narrate_flag_parsed():
    """build_parser 必须解析 --narrate。"""
    from modules.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(["simulate", "000001.SZ", "--narrate"])
    assert args.narrate is True

    args2 = parser.parse_args(["simulate", "000001.SZ"])
    assert args2.narrate is False
