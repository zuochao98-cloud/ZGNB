"""M4: except narrowing tests for monitor.py"""

import sys
import logging

import pytest


class TestMonitorSyncBestEffort:
    """`run_watchlist_monitor` 在同步失败时不抛异常，继续本地扫描"""

    def test_sync_failure_continues_to_scan(self, monkeypatch, caplog):
        from modules import monitor

        # 让 sync 抛错
        class FakeSyncer:
            def __init__(self):
                pass

            def sync_daily_and_compute(self, **kw):
                raise ConnectionError("simulated sync failure")

        monkeypatch.setattr(monitor, "DataSyncer", FakeSyncer)

        # 自选股有内容
        monkeypatch.setattr(monitor, "get_watchlist", lambda: [{"ts_code": "000001.SZ"}])

        # scan_watchlist 返回空 alerts
        monkeypatch.setattr(
            monitor,
            "scan_watchlist",
            lambda: {"alerts": [], "summary": {"total": 0}},
        )
        monkeypatch.setattr(monitor, "generate_daily_report", lambda: "report text")

        with caplog.at_level(logging.ERROR, logger="zettaranc-monitor"):
            result = monitor.run_watchlist_monitor(sync_days=10, enable_push=False)

        # 不应抛异常，应继续走本地扫描路径
        assert result["status"] == "success"
        assert any("DATA_SOURCE_ERROR" in r.message for r in caplog.records)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
