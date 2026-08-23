"""
bridge_client.py 测试
验证 bridge 客户端的降级网关行为
"""

import urllib.error

import pytest
from unittest.mock import patch, MagicMock

from modules.bridge_client import (
    BridgeConfig,
    set_bridge_config,
    is_bridge_available,
    get_bridge_daily,
    get_bridge_stock_list,
    query_bridge_local,
    query_bridge_sql,
    get_daily_klines,
    get_all_stocks_bridge_first,
)


# ============ BridgeConfig 测试 ============


class TestBridgeConfig:
    def test_default_config(self):
        cfg = BridgeConfig()
        assert cfg.host == "127.0.0.1"
        assert cfg.port == 8765
        assert cfg.timeout == 10
        assert cfg.enabled == "auto"
        assert cfg.base_url == "http://127.0.0.1:8765"

    def test_custom_config(self):
        cfg = BridgeConfig(host="192.168.1.1", port=9999, timeout=5, enabled="always")
        assert cfg.base_url == "http://192.168.1.1:9999"
        assert cfg.timeout == 5
        assert cfg.enabled == "always"


# ============ 健康检查测试 ============


class TestIsBridgeAvailable:
    def test_never_enabled(self):
        set_bridge_config(enabled="never")
        assert is_bridge_available() is False

    def test_always_enabled(self):
        set_bridge_config(enabled="always")
        assert is_bridge_available() is True

    @patch("modules.bridge_client._http_get")
    def test_auto_available(self, mock_get):
        set_bridge_config(enabled="auto")
        mock_get.return_value = {"status": "ok"}
        assert is_bridge_available() is True

    @patch("modules.bridge_client._http_get")
    def test_auto_unavailable(self, mock_get):
        set_bridge_config(enabled="auto")
        mock_get.side_effect = urllib.error.URLError("Connection refused")
        assert is_bridge_available() is False


# ============ GET 接口测试 ============


class TestGetBridgeDaily:
    @patch("modules.bridge_client.is_bridge_available")
    def test_bridge_disabled(self, mock_available):
        mock_available.return_value = False
        result = get_bridge_daily("600519.SH", days=30)
        assert result == []

    @patch("modules.bridge_client.is_bridge_available")
    @patch("modules.bridge_client._http_get")
    def test_success(self, mock_get, mock_available):
        mock_available.return_value = True
        mock_get.return_value = {
            "data": [
                {"ts_code": "600519.SH", "trade_date": "20240101", "close": 100},
                {"ts_code": "600519.SH", "trade_date": "20240102", "close": 101},
            ]
        }
        result = get_bridge_daily("600519.SH", days=30)
        assert len(result) == 2
        assert result[0]["trade_date"] == "20240101"
        assert result[1]["trade_date"] == "20240102"

    @patch("modules.bridge_client.is_bridge_available")
    @patch("modules.bridge_client._http_get")
    def test_failure_returns_empty(self, mock_get, mock_available):
        mock_available.return_value = True
        mock_get.side_effect = TimeoutError("Timeout")
        result = get_bridge_daily("600519.SH", days=30)
        assert result == []


class TestGetBridgeStockList:
    @patch("modules.bridge_client.is_bridge_available")
    def test_bridge_disabled(self, mock_available):
        mock_available.return_value = False
        result = get_bridge_stock_list()
        assert result == []

    @patch("modules.bridge_client.is_bridge_available")
    @patch("modules.bridge_client._http_get")
    def test_success(self, mock_get, mock_available):
        mock_available.return_value = True
        mock_get.return_value = {
            "stocks": [
                {"ts_code": "600519.SH", "name": "贵州茅台"},
            ]
        }
        result = get_bridge_stock_list()
        assert len(result) == 1
        assert result[0]["ts_code"] == "600519.SH"


# ============ POST 接口测试 ============


class TestQueryBridgeLocal:
    @patch("modules.bridge_client.is_bridge_available")
    def test_bridge_disabled(self, mock_available):
        mock_available.return_value = False
        result = query_bridge_local("daily", where="ts_code = '600519.SH'")
        assert result == []

    @patch("modules.bridge_client.is_bridge_available")
    @patch("modules.bridge_client._http_post")
    def test_success(self, mock_post, mock_available):
        mock_available.return_value = True
        mock_post.return_value = {"data": [{"ts_code": "600519.SH", "close": 100}]}
        result = query_bridge_local("daily", where="ts_code = '600519.SH'")
        assert len(result) == 1


class TestQueryBridgeSql:
    @patch("modules.bridge_client.is_bridge_available")
    def test_bridge_disabled(self, mock_available):
        mock_available.return_value = False
        result = query_bridge_sql("SELECT * FROM daily_kline LIMIT 1")
        assert result == []

    @patch("modules.bridge_client.is_bridge_available")
    @patch("modules.bridge_client._http_post")
    def test_success(self, mock_post, mock_available):
        mock_available.return_value = True
        mock_post.return_value = {"data": [{"ts_code": "600519.SH"}]}
        result = query_bridge_sql("SELECT * FROM daily_kline LIMIT 1")
        assert len(result) == 1


# ============ 降级网关测试 ============


class TestGetDailyKlines:
    @patch("modules.bridge_client.get_bridge_daily")
    @patch("modules.bridge_client._get_local_daily")
    def test_bridge_success_no_fallback(self, mock_local, mock_bridge):
        mock_bridge.return_value = [{"ts_code": "600519.SH", "trade_date": "20240101", "close": 100}]
        result = get_daily_klines("600519.SH", days=30)
        assert len(result) == 1
        mock_local.assert_not_called()

    @patch("modules.bridge_client.get_bridge_daily")
    @patch("modules.bridge_client._get_local_daily")
    def test_bridge_empty_fallback(self, mock_local, mock_bridge):
        mock_bridge.return_value = []
        mock_local.return_value = [{"ts_code": "600519.SH", "trade_date": "20240101", "close": 100}]
        result = get_daily_klines("600519.SH", days=30)
        assert len(result) == 1
        mock_local.assert_called_once()

    @patch("modules.bridge_client.get_bridge_daily")
    @patch("modules.bridge_client._get_local_daily")
    def test_bridge_failure_fallback(self, mock_local, mock_bridge):
        # mock_bridge 返回空列表 = 模拟 get_bridge_daily 内部捕获异常后返回 []
        mock_bridge.return_value = []
        mock_local.return_value = [{"ts_code": "600519.SH", "trade_date": "20240101", "close": 100}]
        result = get_daily_klines("600519.SH", days=30)
        assert len(result) == 1
        mock_local.assert_called_once()


class TestGetAllStocksBridgeFirst:
    @patch("modules.bridge_client.get_bridge_stock_list")
    @patch("modules.bridge_client._get_local_stock_list")
    def test_bridge_success_no_fallback(self, mock_local, mock_bridge):
        mock_bridge.return_value = [{"ts_code": "600519.SH", "name": "茅台"}]
        result = get_all_stocks_bridge_first()
        assert len(result) == 1
        mock_local.assert_not_called()

    @patch("modules.bridge_client.get_bridge_stock_list")
    @patch("modules.bridge_client._get_local_stock_list")
    def test_bridge_empty_fallback(self, mock_local, mock_bridge):
        mock_bridge.return_value = []
        mock_local.return_value = [{"ts_code": "600519.SH", "name": "茅台"}]
        result = get_all_stocks_bridge_first()
        assert len(result) == 1
        mock_local.assert_called_once()
