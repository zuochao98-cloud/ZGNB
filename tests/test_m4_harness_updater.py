"""M4: except narrowing tests for harness_updater.py"""

import sys
import sqlite3

import pytest


class TestHarnessUpdaterFallback:
    """所有 HarnessUpdater 方法在异常时返回 success=False 结构"""

    def test_analyze_returns_failure_dict_on_db_error(self, monkeypatch):
        from modules import harness_updater as hu
        from contextlib import contextmanager

        @contextmanager
        def boom_conn():
            raise sqlite3.OperationalError("db locked")
            yield  # pragma: no cover

        monkeypatch.setattr("modules.database.get_connection", boom_conn)
        updater = hu.HarnessUpdater()
        result = updater.analyze_strategy_performance("2025-01")
        assert result["success"] is False
        assert "分析策略表现失败" in result["message"]

    def test_generate_guardrails_returns_failure_on_type_error(self):
        from modules import harness_updater as hu

        updater = hu.HarnessUpdater()
        # analysis_result 为 falsy → 直接透传；缺 success 字段 → KeyError 触发 except
        result = updater.generate_guardrails_update({"success": False, "message": "no data"})
        assert result["success"] is False
        assert "no data" in result.get("message", "")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
