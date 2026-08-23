"""M4: except narrowing tests for trade_reviewer.py"""

import sys
from datetime import datetime
from types import SimpleNamespace

import pytest


class TestTradeReviewerEnrichFallback:
    """`enrich_with_indicators` 在指标获取失败时跳过，不抛异常"""

    def test_enrich_continues_when_analyze_fails(self, monkeypatch):
        from modules import trade_reviewer as tr

        def boom(*a, **kw):
            raise ValueError("simulated indicator failure")

        monkeypatch.setattr(tr, "analyze_stock", boom)

        ctx = tr.ReviewContext(
            ts_code="000001.SZ",
            name="测试",
            trade_date=datetime.now().strftime("%Y-%m-%d"),
            action="BUY",
            price=10.0,
            quantity=100,
            amount=1000.0,
            reason="测试",
        )
        result = tr.TradeReviewer().enrich_with_indicators(ctx, days=10)
        # 失败时不应填充 indicators，但 ctx 仍可返回
        assert result.indicators is None


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
