"""M4: except narrowing tests for portfolio_diagnosis.py"""

import sys
import sqlite3

import pytest


class TestPortfolioDiagnosisDbFallback:
    """`get_stock_info_db` 在 DB 异常时返回 None（best-effort 降级）"""

    def test_returns_none_when_db_unavailable(self, monkeypatch):
        from modules import portfolio_diagnosis as pd

        # 强制 get_connection 抛错
        from contextlib import contextmanager

        @contextmanager
        def boom_conn():
            raise sqlite3.OperationalError("db locked")
            yield  # pragma: no cover

        monkeypatch.setattr("modules.database.get_connection", boom_conn)
        result = pd.get_stock_info_db("000001.SZ")
        assert result is None


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
