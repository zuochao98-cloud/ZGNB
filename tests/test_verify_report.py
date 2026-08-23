"""报告输出测试"""

from __future__ import annotations

import json
from pathlib import Path

from modules.verify.pipeline import (
    AggregateMetrics,
    GateResult,
    StockResult,
    VerifyResult,
)
from modules.verify.report import render_json, render_markdown, write_report


def _make_full_result() -> VerifyResult:
    return VerifyResult(
        per_stock=[
            StockResult(
                ts_code="600519.SH",
                name="贵州茅台",
                trades=10,
                win_rate=0.6,
                return_pct=15.0,
                sharpe=1.2,
                max_drawdown=0.10,
            ),
        ],
        aggregate=AggregateMetrics(
            total_trades=100,
            win_rate=0.45,
            total_return_pct=23.0,
            annualized_return=18.0,
            sharpe=0.73,
            calmar=0.61,
            max_drawdown=0.28,
        ),
        gates={
            "sharpe": GateResult("sharpe", 0.73, 0.5, True, ""),
            "max_drawdown": GateResult(
                "max_drawdown",
                0.28,
                0.25,
                False,
                "最大回撤 28% > 25%，建议：收紧止损至 -3%",
            ),
        },
        config_used={"j_threshold": 5, "stop_loss_pct": -0.05},
        meta={"ts_codes_count": 50, "days": 250, "skipped_count": 2},
    )


def test_render_json_has_required_keys():
    """JSON 必须含 timestamp/aggregate/gates/passed_count"""
    result = _make_full_result()
    text = render_json(result)
    data = json.loads(text)
    assert "timestamp" in data
    assert "aggregate" in data
    assert "gates" in data
    assert "passed_count" in data
    assert "total_count" in data


def test_render_markdown_includes_gates():
    """Markdown 报告含五项硬指标表格"""
    result = _make_full_result()
    md = render_markdown(result)
    assert "# 少妇战法 v1.0 验收报告" in md
    assert "| 指标 |" in md
    assert "Sharpe" in md or "夏普" in md
    assert "1/2 通过" in md or "总评" in md


def test_write_report_creates_file_at_path(tmp_path: Path):
    """write_report 同时写 JSON + Markdown 文件"""
    result = _make_full_result()
    paths = write_report(result, output_dir=tmp_path, base_name="test")
    assert paths.json_path.exists()
    assert paths.md_path.exists()
    # JSON 文件能正确 parse
    data = json.loads(paths.json_path.read_text())
    assert data["passed_count"] == 1
    assert data["total_count"] == 2
