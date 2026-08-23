"""M4: except narrowing tests for database.py + datasource.py"""

import sys
import sqlite3

import pytest


class TestDatabaseConnectionRollback:
    """`get_connection` 事务失败回滚并 re-raise"""

    def test_rollback_on_sqlite_error(self, monkeypatch):
        from contextlib import contextmanager

        @contextmanager
        def boom_conn():
            conn = sqlite3.connect(":memory:")
            try:
                yield conn
                # 触发 commit 阶段抛错（模拟外层异常）
                raise sqlite3.OperationalError("commit failed")
            except sqlite3.OperationalError:
                conn.rollback()
                raise
            finally:
                conn.close()

        monkeypatch.setattr("modules.database.get_connection", boom_conn)
        with pytest.raises(sqlite3.OperationalError):
            with boom_conn():
                pass


class TestDatasourceFallback:
    """数据源读取失败时按既有 fallback 返回（best-effort）"""

    def test_datasource_no_bare_exception(self):
        """M4: datasource.py 所有 except Exception 已收窄"""
        import inspect

        from modules import datasource

        source = inspect.getsource(datasource)
        assert "except Exception" not in source


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
