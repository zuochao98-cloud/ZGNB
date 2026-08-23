"""
Z哥量化自选股监视引擎测试
"""

from pathlib import Path
from unittest.mock import patch, MagicMock
from modules.watchlist import add_watch
from modules.monitor import run_watchlist_monitor


def test_monitor_empty(temp_db):
    """自选股为空时，监视应直接返回 empty 状态"""
    res = run_watchlist_monitor(enable_push=False)
    assert res["status"] == "empty"
    assert res["alerts_count"] == 0


@patch("modules.data_sync.DataSyncer.sync_daily_and_compute")
@patch("modules.monitor.scan_watchlist")
@patch("modules.monitor.generate_daily_report")
@patch("modules.monitor.notify_all")
def test_monitor_with_items(mock_notify, mock_report, mock_scan, mock_sync, temp_db, db_conn):
    """测试自选股有数据时的正常扫描流程"""
    from tests.conftest import write_stock_basic

    # 写入测试自选股
    write_stock_basic(db_conn, "600487.SH", "亨通光电")
    add_watch("600487.SH", name="亨通光电")

    # 模拟数据同步、扫描和报告生成
    mock_sync.return_value = {"600487.SH": 1}
    mock_scan.return_value = {
        "alerts": [
            MagicMock(ts_code="600487.SH", name="亨通光电", alert_type="B1", level="INFO", message="出现B1买点")
        ],
        "summary": {"total": 1, "b1_count": 1, "exit_count": 0, "break_count": 0, "abnormal_count": 0},
    }
    mock_report.return_value = "测试自选股每日报告\n600487.SH 亨通光电 出现B1买点"
    mock_notify.return_value = {"macos": True, "feishu": False}

    # 运行监控，应该成功写入文件，并执行通知推送
    res = run_watchlist_monitor(sync_days=5, enable_push=True)

    assert res["status"] == "success"
    assert res["alerts_count"] == 1
    assert res["summary"]["b1_count"] == 1

    # 验证本地报告已写盘
    report_file = Path("data/reports/monitor_alert.md")
    assert report_file.exists()
    assert "测试自选股每日报告" in report_file.read_text(encoding="utf-8")

    # 验证主动通知被触发了
    mock_notify.assert_called_once()
