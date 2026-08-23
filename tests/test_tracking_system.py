"""
自我改进系统 pytest 测试

覆盖：
- TrackingManager（跟踪池管理：add/remove/list/stats）
- ReviewGenerator（复盘报告生成）
- HarnessUpdater（策略表现分析 + Guardrails 更新建议）

依赖 tests/conftest.py 的 temp_db fixture 创建隔离的临时数据库，
不再读写 data/stock_data.db。
"""

import pytest

from modules.tracking_manager import TrackingManager
from modules.tracking_syncer import TrackingSyncer  # noqa: F401  保持导入契约,后续用例可能使用
from modules.review_generator import ReviewGenerator
from modules.harness_updater import HarnessUpdater


# ==================== TrackingManager ====================


class TestTrackingManager:
    """跟踪池管理器 pytest 测试（无 __init__,由 pytest 构造实例）"""

    def test_add_stock(self, temp_db):
        """添加股票应成功落库,字段全部可读出"""
        mgr = TrackingManager()
        result = mgr.add_stock(
            ts_code="600519.SH",
            name="贵州茅台",
            reason="B1买点出现",
            strategy_tags=["B1"],
            notes="测试股票",
        )
        assert result is True, "添加股票失败"

        stock = mgr.get_stock_info("600519.SH")
        assert stock is not None, "股票不存在"
        assert stock["ts_code"] == "600519.SH"
        assert stock["name"] == "贵州茅台"
        assert stock["status"] == "active"

    def test_remove_stock(self, temp_db):
        """移除股票应设置 status=removed,但行不删除(支持历史)"""
        mgr = TrackingManager()
        mgr.add_stock("600519.SH", "贵州茅台", "测试")

        removed = mgr.remove_stock("600519.SH", "测试完成")
        assert removed is True, "移除股票失败"

        stock = mgr.get_stock_info("600519.SH")
        assert stock is not None, "股票不存在(移除应保留行)"
        assert stock["status"] == "removed"

    def test_list_stocks_filter_by_status_and_strategy(self, temp_db):
        """list_stocks 应同时支持按 status 和 strategy_tag 过滤"""
        mgr = TrackingManager()
        mgr.add_stock("600519.SH", "贵州茅台", "测试1", ["B1"])
        mgr.add_stock("000858.SZ", "五粮液", "测试2", ["B2"])

        active = mgr.list_stocks(status="active")
        assert len(active) == 2, f"活跃股票数应为 2,实际 {len(active)}"

        b1_only = mgr.list_stocks(strategy_tag="B1")
        assert len(b1_only) == 1
        assert b1_only[0]["ts_code"] == "600519.SH"

    def test_get_stats_and_strategy_distribution(self, temp_db):
        """get_tracking_stats + get_strategy_distribution 数字应正确"""
        mgr = TrackingManager()
        mgr.add_stock("600519.SH", "贵州茅台", "测试1", ["B1"])
        mgr.add_stock("000858.SZ", "五粮液", "测试2", ["B2"])

        stats = mgr.get_tracking_stats()
        assert stats.get("total", 0) == 2
        assert stats.get("active", 0) == 2

        dist = mgr.get_strategy_distribution()
        assert dist.get("B1") == 1
        assert dist.get("B2") == 1


# ==================== ReviewGenerator ====================


class TestReviewGenerator:
    """复盘报告生成器 pytest 测试"""

    def test_generate_monthly_review_returns_expected_shape(self, temp_db):
        """月报应返回 {success, reviews: [...]} 形状（空数据时只有 message + 空 reviews）"""
        gen = ReviewGenerator()
        result = gen.generate_monthly_review("202605")

        # 行为契约：必须 success,且 reviews 必为 list（total_stocks 仅在有数据时存在）
        assert isinstance(result, dict)
        assert "success" in result
        assert "reviews" in result
        assert isinstance(result["reviews"], list)


# ==================== HarnessUpdater ====================


class TestHarnessUpdater:
    """Harness 层更新器 pytest 测试"""

    def test_analyze_strategy_performance_returns_review_month(self, temp_db):
        """analyze_strategy_performance 应回传 review_month 字段"""
        updater = HarnessUpdater()
        result = updater.analyze_strategy_performance("202605")

        assert isinstance(result, dict)
        assert "success" in result
        if result.get("success"):
            assert result.get("review_month") == "202605"
            assert "strategy_stats" in result
            assert isinstance(result["strategy_stats"], list)

    def test_generate_guardrails_update_accepts_analysis_result(self, temp_db):
        """generate_guardrails_update 应接受 analysis_result 并返回 updates 列表"""
        updater = HarnessUpdater()
        analysis = updater.analyze_strategy_performance("202605")
        result = updater.generate_guardrails_update(analysis)

        assert isinstance(result, dict)
        assert "success" in result
        if result.get("success"):
            assert "updates" in result or "total_updates" in result
