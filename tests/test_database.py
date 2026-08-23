"""
database.py 单元测试
"""

import pytest


class TestGetDbPath:
    """数据库路径解析测试"""

    def test_path_is_absolute(self, mock_env_for_tests):
        from modules.database import get_db_path

        path = get_db_path()
        assert path.is_absolute()

    def test_parent_dir_created(self, mock_env_for_tests):
        from modules.database import get_db_path

        path = get_db_path()
        assert path.parent.exists()


class TestGetConnection:
    """数据库连接测试"""

    def test_connection_returns_context(self, temp_db):
        from modules.database import get_connection

        with get_connection() as conn:
            assert conn is not None
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1

    def test_connection_has_row_factory(self, temp_db):
        from modules.database import get_connection

        with get_connection() as conn:
            assert conn.row_factory is not None

    def test_commit_on_success(self, temp_db):
        from modules.database import get_connection

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_table (
                    id INTEGER PRIMARY KEY,
                    name TEXT
                )
            """)
            cursor.execute("INSERT INTO test_table (id, name) VALUES (1, 'test')")
        # 退出 context 后应该已提交
        from modules.database import get_connection as gc2

        with gc2() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM test_table WHERE id = 1")
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == "test"

    def test_rollback_on_error(self, temp_db):
        from modules.database import get_connection

        # 先创建表
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_rollback (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """)
        # 插入失败应该回滚
        with pytest.raises(Exception):
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO test_rollback (id, name) VALUES (1, NULL)")


class TestInitDatabase:
    """数据库初始化测试"""

    def test_creates_tables(self, temp_db):
        from modules.database import get_connection

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = {row[0] for row in cursor.fetchall()}
            expected = {
                "daily_kline",
                "indicator_cache",
                "moneyflow",
                "financial_data",
                "stock_basic",
                "trade_signals",
                "sync_log",
            }
            assert expected.issubset(tables)

    def test_creates_indexes(self, temp_db):
        from modules.database import get_connection

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master WHERE type='index'
            """)
            indexes = {row[0] for row in cursor.fetchall()}
            assert "idx_kline_code_date" in indexes
            assert "idx_ind_date" in indexes
            assert "idx_mf_code_date" in indexes

    def test_idempotent(self, temp_db):
        """多次调用不应报错"""
        from modules.database import init_database

        init_database()
        init_database()  # 第二次不应失败


class TestLLMResponseLog:
    """LLM 响应耗时日志测试"""

    def test_table_exists(self, temp_db):
        """llm_response_log 表应被 init_database 创建"""
        from modules.database import get_connection

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='llm_response_log'
            """)
            assert cursor.fetchone() is not None

    def test_indexes_exist(self, temp_db):
        """三个索引都应存在"""
        from modules.database import get_connection

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='index' AND tbl_name='llm_response_log'
            """)
            indexes = {row[0] for row in cursor.fetchall()}
            assert "idx_llm_log_code_date" in indexes
            assert "idx_llm_log_date" in indexes
            assert "idx_llm_log_model" in indexes

    def test_record_llm_response_success(self, temp_db):
        """记录一次成功调用"""
        from modules.database import record_llm_response, get_llm_response_log

        record_llm_response(
            ts_code="600519.SH",
            model="MiniMax-M3",
            response_time_ms=1234.5,
            success=True,
            request_date="2026-06-15",
        )
        rows = get_llm_response_log(ts_code="600519.SH")
        assert len(rows) == 1
        row = rows[0]
        assert row["ts_code"] == "600519.SH"
        assert row["model"] == "MiniMax-M3"
        assert row["response_time_ms"] == 1234.5
        assert row["success"] == 1
        assert row["error_message"] == ""
        assert row["request_date"] == "2026-06-15"

    def test_record_llm_response_failure(self, temp_db):
        """记录一次失败调用"""
        from modules.database import record_llm_response, get_llm_response_log

        record_llm_response(
            ts_code="000001.SZ",
            model="MiniMax-M3",
            response_time_ms=500.0,
            success=False,
            error_message="API timeout",
            request_date="2026-06-15",
        )
        rows = get_llm_response_log(ts_code="000001.SZ")
        assert len(rows) == 1
        assert rows[0]["success"] == 0
        assert rows[0]["error_message"] == "API timeout"

    def test_request_date_defaults_to_today(self, temp_db):
        """不传 request_date 时应使用当天日期"""
        from modules.database import record_llm_response, get_llm_response_log, get_connection

        record_llm_response(
            ts_code="600519.SH",
            model="MiniMax-M3",
            response_time_ms=100.0,
        )
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT date('now', 'localtime')")
            today = cursor.fetchone()[0]
        rows = get_llm_response_log(ts_code="600519.SH", request_date=today)
        assert len(rows) == 1

    def test_get_log_filter_by_model(self, temp_db):
        """按模型过滤"""
        from modules.database import record_llm_response, get_llm_response_log

        record_llm_response("600519.SH", "MiniMax-M3", 100.0, request_date="2026-06-15")
        record_llm_response("600519.SH", "MiniMax-M2", 200.0, request_date="2026-06-15")

        m3_rows = get_llm_response_log(model="MiniMax-M3", request_date="2026-06-15")
        m2_rows = get_llm_response_log(model="MiniMax-M2", request_date="2026-06-15")
        assert len(m3_rows) == 1
        assert len(m2_rows) == 1
        assert m3_rows[0]["model"] == "MiniMax-M3"
        assert m2_rows[0]["model"] == "MiniMax-M2"

    def test_stats_aggregation(self, temp_db):
        """日聚合统计"""
        from modules.database import record_llm_response, get_llm_response_stats

        record_llm_response("600519.SH", "MiniMax-M3", 100.0, success=True, request_date="2026-06-15")
        record_llm_response("600519.SH", "MiniMax-M3", 200.0, success=True, request_date="2026-06-15")
        record_llm_response("600519.SH", "MiniMax-M3", 300.0, success=False, request_date="2026-06-15")
        # 不同日期不应被聚合进来
        record_llm_response("600519.SH", "MiniMax-M3", 9999.0, success=True, request_date="2026-06-14")

        stats = get_llm_response_stats(request_date="2026-06-15")
        assert stats["total_calls"] == 3
        assert stats["success_calls"] == 2
        assert stats["failed_calls"] == 1
        assert stats["avg_ms"] == 200.0  # (100+200+300)/3
        assert stats["max_ms"] == 300.0
        assert stats["min_ms"] == 100.0

    def test_stats_empty_day(self, temp_db):
        """没有数据的天应返回全 0 统计"""
        from modules.database import get_llm_response_stats

        stats = get_llm_response_stats(request_date="2020-01-01")
        assert stats["total_calls"] == 0
        assert stats["success_calls"] == 0
        assert stats["failed_calls"] == 0
        assert stats["avg_ms"] == 0.0


class TestDropAllTables:
    """删除表测试"""

    def test_drops_all_tables(self, temp_db):
        from modules.database import drop_all_tables, init_database

        # 先初始化
        init_database()
        # 再删除
        drop_all_tables()
        # 验证
        from modules.database import get_connection

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = cursor.fetchall()
            assert len(tables) == 0

    def test_reinit_after_drop(self, temp_db):
        from modules.database import drop_all_tables, init_database

        init_database()
        drop_all_tables()
        init_database()  # 删除后重新初始化应成功
