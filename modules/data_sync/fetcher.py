"""Data fetcher wrapping a DataSource."""

from __future__ import annotations
from typing import Any

import pandas as pd

from ..datasource import DataSource


class DataFetcher:
    """Encapsulates raw data pulling from a DataSource."""

    def __init__(self, datasource: DataSource) -> None:
        self.datasource = datasource

    def fetch_stock_basic(self) -> pd.DataFrame | None:
        """拉取股票基础信息。"""
        return self.datasource.get_stock_basic()

    def fetch_daily_kline(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame | None:
        """拉取个股日 K 线。"""
        return self.datasource.get_daily(ts_code, start_date, end_date)

    def fetch_stk_factor(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame | None:
        """拉取个股技术因子。"""
        return self.datasource.get_stk_factor(ts_code, start_date, end_date)

    def fetch_daily_basic(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame | None:
        """拉取个股每日基础指标。"""
        return self.datasource.get_daily_basic(ts_code, start_date, end_date)

    def fetch_moneyflow(self, ts_code: str, trade_date: str) -> pd.DataFrame | None:
        """拉取个股单日资金流向。"""
        return self.datasource.get_moneyflow(ts_code, trade_date)
