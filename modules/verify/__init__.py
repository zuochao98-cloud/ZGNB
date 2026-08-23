"""v1.0 验收工程化子包"""

from .pipeline import (
    AggregateMetrics,
    GateResult,
    StockResult,
    VerifyResult,
    verify_v10_pipeline,
)
from .report import (
    ReportPaths,
    render_json,
    render_markdown,
    write_report,
)
from .cli import build_parser, run_verify_v10, main as verify_cli_main
from .scorer import V10ScoreResult, V10VerifyScorer

__all__ = [
    "AggregateMetrics",
    "GateResult",
    "ReportPaths",
    "StockResult",
    "VerifyResult",
    "V10ScoreResult",
    "V10VerifyScorer",
    "build_parser",
    "render_json",
    "render_markdown",
    "run_verify_v10",
    "verify_cli_main",
    "verify_v10_pipeline",
    "write_report",
]
