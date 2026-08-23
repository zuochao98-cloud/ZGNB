"""screener data 层 DataSource 注入测试。"""

import pytest

from modules.screener.data import get_all_stocks, get_recent_klines


class FakeDataSource:
    """用于测试 DataSource 注入的伪数据源"""

    def __init__(self, stocks=None, klines=None):
        self._stocks = stocks or []
        self._klines = klines or []

    @property
    def name(self):
        return "fake"

    def get_stock_list(self):
        return list(self._stocks)

    def get_kline_dicts(self, ts_code, days=60, start_date=None, end_date=None):
        return [dict(row) for row in self._klines[-days:]]


class TestGetAllStocksInjection:
    def test_uses_injected_datasource(self):
        fake = FakeDataSource(
            stocks=[
                {"ts_code": "000001.SZ", "name": "平安银行", "market": "主板"},
                {"ts_code": "300001.SZ", "name": "特锐德", "market": "创业板"},
                {"ts_code": "999999.XX", "name": "未知板块", "market": "B股"},
            ]
        )
        result = get_all_stocks(datasource=fake)
        assert len(result) == 2
        assert {s["ts_code"] for s in result} == {"000001.SZ", "300001.SZ"}

    def test_fallback_when_empty(self, temp_db):
        fake = FakeDataSource(stocks=[])
        result = get_all_stocks(datasource=fake)
        assert isinstance(result, list)


class TestGetRecentKlinesInjection:
    def test_uses_injected_datasource(self):
        klines = [
            {
                "ts_code": "000001.SZ",
                "trade_date": "20260101",
                "open": 10.0,
                "high": 11.0,
                "low": 9.0,
                "close": 10.5,
                "vol": 1000,
                "amount": 10500.0,
                "pct_chg": 5.0,
            },
            {
                "ts_code": "000001.SZ",
                "trade_date": "20260102",
                "open": 10.5,
                "high": 11.5,
                "low": 10.0,
                "close": 11.0,
                "vol": 2000,
                "amount": 22000.0,
                "pct_chg": 4.76,
            },
        ]
        fake = FakeDataSource(klines=klines)
        result = get_recent_klines("000001.SZ", days=60, datasource=fake)
        assert len(result) == 2
        assert result[0].trade_date == "20260101"
        assert result[1].trade_date == "20260102"
        assert result[1].prev_close == 10.5

    def test_returns_empty_when_no_data(self):
        fake = FakeDataSource(klines=[])
        result = get_recent_klines("000001.SZ", datasource=fake)
        assert result == []
