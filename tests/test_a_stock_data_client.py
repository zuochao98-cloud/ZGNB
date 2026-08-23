"""a_stock_data_client.py 测试 — 免费 A 股公开接口客户端（全 mock，零网络）"""

import sys
import types
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

import modules.a_stock_data_client as m
from modules.a_stock_data_client import (
    AStockDataClient,
    _6digit_to_ts_code,
    _eastmoney_datacenter,
    _em_get,
    _get_market_code,
    _get_prefix,
    _mootdx_kline,
    _ts_code_to_6digit,
    baidu_kline_to_dataframe,
    baidu_kline_with_ma,
    eastmoney_fund_flow_minute,
    eastmoney_stock_info,
    stock_fund_flow_120d,
    tencent_quote,
)


# ==================== 测试数据工厂 ====================


def _make_tencent_line(code: str, prefix: str = "sh", name: str = "贵州茅台") -> str:
    """构造一条逼真的腾讯行情行（53 个 ~ 分隔字段，不含结尾分号）"""
    vals = ["0"] * 53
    vals[0] = "1"
    vals[1] = name
    vals[2] = code
    vals[3] = "1500.00"  # 现价
    vals[4] = "1490.00"  # 昨收
    vals[5] = "1495.00"  # 今开
    vals[31] = "10.00"  # 涨跌额
    vals[32] = "0.67"  # 涨跌幅 %
    vals[33] = "1510.00"  # 最高
    vals[34] = "1480.00"  # 最低
    vals[37] = "500000.00"  # 成交额（万）
    vals[38] = "1.23"  # 换手率 %
    vals[39] = "25.60"  # PE TTM
    vals[43] = "2.01"  # 振幅 %
    vals[44] = "18843.00"  # 总市值（亿）
    vals[45] = "18000.00"  # 流通市值（亿）
    vals[46] = "8.50"  # PB
    vals[47] = "1639.00"  # 涨停价
    vals[48] = "1341.00"  # 跌停价
    vals[49] = "1.05"  # 量比
    vals[52] = "26.10"  # 静态 PE
    body = "~".join(vals)
    return f'v_{prefix}{code}="{body}"'


def _mock_urlopen_text(mock_urlopen, text: str) -> None:
    """让 mocked urlopen 返回 GBK 编码文本（模拟腾讯接口编码）"""
    mock_resp = MagicMock()
    mock_resp.read.return_value = text.encode("gbk")
    mock_urlopen.return_value = mock_resp


def _make_quote_dict() -> dict:
    """tencent_quote 解析后的 dict（用于 mock tencent_quote 本身）"""
    return {
        "name": "贵州茅台",
        "price": 1500.0,
        "last_close": 1490.0,
        "open": 1495.0,
        "change_amt": 10.0,
        "change_pct": 0.67,
        "high": 1510.0,
        "low": 1480.0,
        "amount_wan": 500000.0,
        "turnover_pct": 1.23,
        "pe_ttm": 25.6,
        "amplitude_pct": 2.01,
        "mcap_yi": 18843.0,
        "float_mcap_yi": 18000.0,
        "pb": 8.5,
        "limit_up": 1639.0,
        "limit_down": 1341.0,
        "vol_ratio": 1.05,
        "pe_static": 26.1,
    }


def _make_baidu_payload(rows: list) -> dict:
    """构造逼真的百度股市通 K 线 JSON（keys + 分号分隔行）"""
    keys = ["time", "open", "high", "low", "close", "volume", "amount", "ma5", "ma10", "ma20"]
    return {"Result": {"newMarketData": {"keys": keys, "marketData": ";".join(rows)}}}


_BAIDU_ROWS_3 = [
    "2026-07-20,10.00,10.50,9.90,10.20,10000,1020000,10.10,10.05,10.00",
    "2026-07-21,10.20,10.60,10.10,10.50,12000,1260000,10.20,10.10,10.05",
    "2026-07-22,10.50,10.80,10.40,10.70,11000,1177000,10.30,10.15,10.10",
]


def _mock_requests_get(mock_get, payload) -> None:
    """让 mocked requests.get 返回指定 JSON"""
    mock_resp = MagicMock()
    mock_resp.json.return_value = payload
    mock_get.return_value = mock_resp


def _make_kline_df(dates=("20260720", "20260721", "20260722")) -> pd.DataFrame:
    """构造百度 K 线转换后的 DataFrame（不含 ts_code，由 client 方法补上）"""
    n = len(dates)
    return pd.DataFrame(
        {
            "trade_date": list(dates),
            "open": [10.0 + i for i in range(n)],
            "high": [10.5 + i for i in range(n)],
            "low": [9.9 + i for i in range(n)],
            "close": [10.2 + i for i in range(n)],
            "vol": [10000.0 + i * 100 for i in range(n)],
            "amount": [102000.0 + i * 1000 for i in range(n)],
            "pct_chg": [0.0] * n,
        }
    )


def _install_fake_mootdx(monkeypatch, bars) -> tuple:
    """安装假的 mootdx 模块到 sys.modules，返回 (Quotes 类 mock, client mock)"""
    fake_pkg = types.ModuleType("mootdx")
    fake_quotes_mod = types.ModuleType("mootdx.quotes")
    mock_client = MagicMock()
    mock_client.bars.return_value = bars
    mock_quotes_cls = MagicMock()
    mock_quotes_cls.factory.return_value = mock_client
    fake_quotes_mod.Quotes = mock_quotes_cls
    fake_pkg.quotes = fake_quotes_mod
    monkeypatch.setitem(sys.modules, "mootdx", fake_pkg)
    monkeypatch.setitem(sys.modules, "mootdx.quotes", fake_quotes_mod)
    return mock_quotes_cls, mock_client


def _make_tdx_bars(n: int = 10) -> pd.DataFrame:
    """构造 mootdx bars 返回的 DataFrame（datetime 带时分秒）"""
    return pd.DataFrame(
        {
            "datetime": [f"2026-07-{20 + i:02d} 15:00:00" for i in range(n)],
            "open": [10.0 + i for i in range(n)],
            "high": [10.5 + i for i in range(n)],
            "low": [9.9 + i for i in range(n)],
            "close": [10.2 + i for i in range(n)],
            "vol": [10000.0 + i * 100 for i in range(n)],
            "amount": [102000.0 + i * 1000 for i in range(n)],
        }
    )


# ==================== 代码转换工具函数 ====================


class TestCodeConversion:
    """tushare 代码 <-> 6 位代码 / 市场前缀转换"""

    def test_ts_code_to_6digit(self):
        """000001.SZ / 600519.SH / 北交所 均取点前 6 位"""
        assert _ts_code_to_6digit("000001.SZ") == "000001"
        assert _ts_code_to_6digit("600519.SH") == "600519"
        assert _ts_code_to_6digit("830799.BJ") == "830799"

    def test_ts_code_to_6digit_edge(self):
        """空串与纯 6 位代码原样/安全返回"""
        assert _ts_code_to_6digit("") == ""
        assert _ts_code_to_6digit("000001") == "000001"

    def test_6digit_to_ts_code(self):
        """6 位代码按号段补后缀：6/9->SH，8->BJ，其余->SZ"""
        assert _6digit_to_ts_code("000001") == "000001.SZ"
        assert _6digit_to_ts_code("300750") == "300750.SZ"
        assert _6digit_to_ts_code("600519") == "600519.SH"
        assert _6digit_to_ts_code("900901") == "900901.SH"
        assert _6digit_to_ts_code("830799") == "830799.BJ"
        assert _6digit_to_ts_code("688981") == "688981.SH"

    def test_6digit_to_ts_code_edge(self):
        """空串返回空串；已带后缀的代码原样返回"""
        assert _6digit_to_ts_code("") == ""
        assert _6digit_to_ts_code("600519.SH") == "600519.SH"

    def test_get_market_code(self):
        """东财市场代码：6/9 开头为 1（SH），其余为 0（SZ/BJ）"""
        assert _get_market_code("600519") == 1
        assert _get_market_code("900901") == 1
        assert _get_market_code("000001") == 0
        assert _get_market_code("830799") == 0

    def test_get_prefix(self):
        """行情前缀：6/9->sh，8->bj，其余->sz"""
        assert _get_prefix("600519") == "sh"
        assert _get_prefix("688981") == "sh"
        assert _get_prefix("830799") == "bj"
        assert _get_prefix("000001") == "sz"
        assert _get_prefix("300750") == "sz"


# ==================== 腾讯财经实时行情 ====================


class TestTencentQuote:
    """腾讯财经 qt.gtimg.cn 实时行情解析"""

    @patch("urllib.request.urlopen")
    def test_parse_single_quote(self, mock_urlopen):
        """单条行情：字段名与数值类型正确解析"""
        text = _make_tencent_line("600519", "sh") + ";"
        _mock_urlopen_text(mock_urlopen, text)

        result = tencent_quote(["600519"])
        assert set(result.keys()) == {"600519"}
        q = result["600519"]
        assert q["name"] == "贵州茅台"
        assert q["price"] == 1500.0
        assert isinstance(q["price"], float)
        assert q["last_close"] == 1490.0
        assert q["open"] == 1495.0
        assert q["change_amt"] == 10.0
        assert q["change_pct"] == pytest.approx(0.67)
        assert q["high"] == 1510.0
        assert q["low"] == 1480.0
        assert q["amount_wan"] == 500000.0
        assert q["turnover_pct"] == pytest.approx(1.23)
        assert q["pe_ttm"] == pytest.approx(25.6)
        assert q["amplitude_pct"] == pytest.approx(2.01)
        assert q["mcap_yi"] == 18843.0
        assert q["float_mcap_yi"] == 18000.0
        assert q["pb"] == pytest.approx(8.5)
        assert q["limit_up"] == 1639.0
        assert q["limit_down"] == 1341.0
        assert q["vol_ratio"] == pytest.approx(1.05)
        assert q["pe_static"] == pytest.approx(26.1)

    @patch("urllib.request.urlopen")
    def test_parse_multiple_and_url_prefix(self, mock_urlopen):
        """批量代码：ts_code 输入转 6 位，URL 拼接 sh/sz 前缀，GBK 中文正常解码"""
        text = _make_tencent_line("600519", "sh") + ";\n" + _make_tencent_line("000001", "sz", "平安银行") + ";"
        _mock_urlopen_text(mock_urlopen, text)

        result = tencent_quote(["600519.SH", "000001"])
        assert set(result.keys()) == {"600519", "000001"}
        assert result["000001"]["name"] == "平安银行"

        req = mock_urlopen.call_args[0][0]
        assert "sh600519,sz000001" in req.full_url

    @patch("urllib.request.urlopen")
    def test_dirty_lines_skipped(self, mock_urlopen):
        """脏行跳过：字段不足 53 个 / 无等号分隔的行不进入结果"""
        short_line = 'v_sh600001="1~短行~600001~10.0"'
        garbage_line = "garbage line without separator"
        text = short_line + ";" + garbage_line + ";" + _make_tencent_line("600519") + ";"
        _mock_urlopen_text(mock_urlopen, text)

        result = tencent_quote(["600519"])
        assert set(result.keys()) == {"600519"}

    @patch("urllib.request.urlopen")
    def test_empty_response(self, mock_urlopen):
        """空响应返回空 dict"""
        _mock_urlopen_text(mock_urlopen, "")
        assert tencent_quote(["600519"]) == {}


# ==================== 百度股市通 K 线 ====================


class TestBaiduKline:
    """百度股市通 K 线 JSON 解析与 DataFrame 转换"""

    @patch("modules.a_stock_data_client.requests.get")
    def test_with_ma_normal(self, mock_get):
        """正常 JSON：keys 与按分号拆分的 rows 正确返回"""
        _mock_requests_get(mock_get, _make_baidu_payload(_BAIDU_ROWS_3))

        data = baidu_kline_with_ma("600519")
        assert data["keys"][0] == "time"
        assert len(data["rows"]) == 3
        assert mock_get.call_args.kwargs["params"]["code"] == "600519"

    @patch("modules.a_stock_data_client.requests.get")
    def test_with_ma_result_is_list(self, mock_get):
        """空结果时百度返回 Result=[]：返回空结构而非抛错"""
        _mock_requests_get(mock_get, {"Result": []})
        assert baidu_kline_with_ma("600519") == {"keys": [], "rows": []}

    @patch("modules.a_stock_data_client.requests.get")
    def test_with_ma_bad_structure(self, mock_get):
        """Result 缺失 / newMarketData 非 dict：均返回空结构"""
        _mock_requests_get(mock_get, {"Result": None})
        assert baidu_kline_with_ma("600519") == {"keys": [], "rows": []}

        _mock_requests_get(mock_get, {"Result": {"newMarketData": "bad"}})
        assert baidu_kline_with_ma("600519") == {"keys": [], "rows": []}

    @patch("modules.a_stock_data_client.requests.get")
    def test_to_dataframe_normal(self, mock_get):
        """列名映射对齐 tushare、日期去横杠升序保留、数值化与 pct_chg 计算"""
        _mock_requests_get(mock_get, _make_baidu_payload(_BAIDU_ROWS_3))

        df = baidu_kline_to_dataframe("600519")
        assert df is not None
        for col in ["trade_date", "open", "high", "low", "close", "vol", "amount", "pct_chg"]:
            assert col in df.columns
        # 日期去横杠且保持升序
        assert df["trade_date"].tolist() == ["20260720", "20260721", "20260722"]
        assert df["trade_date"].tolist() == sorted(df["trade_date"].tolist())
        # 数值类型
        assert df["close"].tolist() == [10.2, 10.5, 10.7]
        assert df["vol"].tolist() == [10000, 12000, 11000]
        # 涨跌幅：首日置 0，次日按收盘价比计算
        assert df["pct_chg"].iloc[0] == 0.0
        assert df["pct_chg"].iloc[1] == pytest.approx((10.5 / 10.2 - 1) * 100)

    @patch("modules.a_stock_data_client.requests.get")
    def test_to_dataframe_dirty_rows_filtered(self, mock_get):
        """字段数不足的脏行被丢弃，正常行保留"""
        rows = ["2026-07-20,10.00,10.50"] + _BAIDU_ROWS_3[1:]
        _mock_requests_get(mock_get, _make_baidu_payload(rows))

        df = baidu_kline_to_dataframe("600519")
        assert df is not None
        assert len(df) == 2
        assert df["trade_date"].tolist() == ["20260721", "20260722"]

    @patch("modules.a_stock_data_client.requests.get")
    def test_to_dataframe_all_dirty_returns_none(self, mock_get):
        """所有行都是脏行时返回 None"""
        _mock_requests_get(mock_get, _make_baidu_payload(["bad,row", ""]))
        assert baidu_kline_to_dataframe("600519") is None

    @patch("modules.a_stock_data_client.requests.get")
    def test_to_dataframe_empty_returns_none(self, mock_get):
        """keys/rows 为空时返回 None"""
        _mock_requests_get(mock_get, {"Result": []})
        assert baidu_kline_to_dataframe("600519") is None

    @patch("modules.a_stock_data_client.requests.get")
    def test_to_dataframe_days_limit(self, mock_get):
        """days 限制取尾部最近 N 天，顺序仍升序"""
        rows5 = [f"2026-07-2{i},10.00,10.50,9.90,10.20,10000,1020000,10.10,10.05,10.00" for i in range(5)]
        _mock_requests_get(mock_get, _make_baidu_payload(rows5))

        df = baidu_kline_to_dataframe("600519", days=2)
        assert df is not None
        assert len(df) == 2
        assert df["trade_date"].tolist() == ["20260723", "20260724"]


# ==================== 东财统一请求入口（限流 + 异常兜底） ====================


class TestEmGet:
    """_em_get：1s 节流间隔控制与请求异常返回 None"""

    def test_sleeps_when_interval_too_short(self, monkeypatch):
        """距上次调用不足 1s 时 sleep 补齐（间隔 + 随机抖动）"""
        sleeps = []
        monkeypatch.setattr(m, "_em_last_call", [999.8])
        monkeypatch.setattr(m.time, "time", lambda: 1000.0)
        monkeypatch.setattr(m.time, "sleep", lambda s: sleeps.append(s))
        monkeypatch.setattr(m.random, "uniform", lambda a, b: 0.2)
        mock_resp = MagicMock()
        monkeypatch.setattr(m._EM_SESSION, "get", lambda *a, **k: mock_resp)

        r = _em_get("https://push2.eastmoney.com/api/qt/stock/get")
        assert r is mock_resp
        assert len(sleeps) == 1
        # wait = 1.0 - (1000.0 - 999.8) = 0.8，加抖动 0.2
        assert sleeps[0] == pytest.approx(1.0)

    def test_no_sleep_when_interval_enough(self, monkeypatch):
        """距上次调用超过 1s 时不 sleep"""
        sleeps = []
        monkeypatch.setattr(m, "_em_last_call", [0.0])
        monkeypatch.setattr(m.time, "time", lambda: 1000.0)
        monkeypatch.setattr(m.time, "sleep", lambda s: sleeps.append(s))
        mock_resp = MagicMock()
        monkeypatch.setattr(m._EM_SESSION, "get", lambda *a, **k: mock_resp)

        r = _em_get("https://push2.eastmoney.com/api/qt/stock/get")
        assert r is mock_resp
        assert sleeps == []

    def test_request_exception_returns_none(self, monkeypatch):
        """请求异常返回 None 不抛错，且 finally 仍更新上次调用时间"""
        monkeypatch.setattr(m, "_em_last_call", [0.0])
        monkeypatch.setattr(m.time, "time", lambda: 1000.0)
        monkeypatch.setattr(m.time, "sleep", lambda s: None)

        def _raise(*args, **kwargs):
            raise requests.ConnectionError("boom")

        monkeypatch.setattr(m._EM_SESSION, "get", _raise)

        assert _em_get("https://push2.eastmoney.com/api/qt/stock/get") is None
        assert m._em_last_call[0] == 1000.0


# ==================== 东财数据中心 / 个股信息 / 资金流向 ====================


class TestEastmoneyDatacenter:
    """东财数据中心统一查询"""

    @patch("modules.a_stock_data_client._em_get")
    def test_normal(self, mock_em_get):
        """result.data 列表正确提取"""
        _mock_requests_get(mock_em_get, {"result": {"data": [{"SECURITY_CODE": "600519"}]}})
        rows = _eastmoney_datacenter("RPT_DAILYBILLBOARD_DETAILS")
        assert rows == [{"SECURITY_CODE": "600519"}]

    @patch("modules.a_stock_data_client._em_get")
    def test_empty_and_request_fail(self, mock_em_get):
        """无 result / 请求失败（_em_get 返回 None）：均返回空列表"""
        _mock_requests_get(mock_em_get, {"result": None})
        assert _eastmoney_datacenter("RPT_XXX") == []

        mock_em_get.return_value = None
        assert _eastmoney_datacenter("RPT_XXX") == []


class TestEastmoneyStockInfo:
    """东财个股基本面信息解析"""

    @patch("modules.a_stock_data_client._em_get")
    def test_normal(self, mock_em_get):
        """f 系列字段映射为友好字段名，SH 代码 secid 前缀为 1."""
        payload = {
            "data": {
                "f57": "600519",
                "f58": "贵州茅台",
                "f127": "白酒",
                "f84": 1256197800,
                "f85": 1256197800,
                "f116": 1884296700000,
                "f117": 1884296700000,
                "f189": 20010827,
                "f43": 150000,
            }
        }
        _mock_requests_get(mock_em_get, payload)

        info = eastmoney_stock_info("600519")
        assert mock_em_get.call_args.kwargs["params"]["secid"] == "1.600519"
        assert info["code"] == "600519"
        assert info["name"] == "贵州茅台"
        assert info["industry"] == "白酒"
        assert info["total_shares"] == 1256197800
        assert info["mcap"] == 1884296700000
        assert info["list_date"] == "20010827"
        assert info["price"] == 150000

    @patch("modules.a_stock_data_client._em_get")
    def test_request_fail_returns_empty(self, mock_em_get):
        """请求失败返回空 dict 不抛错"""
        mock_em_get.return_value = None
        assert eastmoney_stock_info("600519") == {}

    @patch("modules.a_stock_data_client._em_get")
    def test_null_data_and_bad_json(self, mock_em_get):
        """data 为 null / JSON 解析失败：返回空 dict 或缺省值，不抛错"""
        _mock_requests_get(mock_em_get, {"data": None})
        info = eastmoney_stock_info("600519")
        assert info["name"] == ""
        assert info["total_shares"] == 0

        mock_resp = MagicMock()
        mock_resp.json.side_effect = ValueError("invalid json")
        mock_em_get.return_value = mock_resp
        assert eastmoney_stock_info("600519") == {}

    @patch("modules.a_stock_data_client._em_get")
    def test_list_payload_returns_empty(self, mock_em_get):
        """异常响应返回 JSON 数组（list）：按空数据处理，不抛 AttributeError"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"msg": "error"}]
        mock_em_get.return_value = mock_resp
        info = eastmoney_stock_info("600519")
        assert info["name"] == ""
        assert info["total_shares"] == 0


class TestEastmoneyFundFlow:
    """东财资金流向（分钟级 / 120 日日级）解析"""

    @patch("modules.a_stock_data_client._em_get")
    def test_minute_normal(self, mock_em_get):
        """分钟级：klines 逗号拆分映射为 time/main/small/mid/large/super"""
        payload = {
            "data": {
                "klines": [
                    "2026-07-24 09:31,100.0,-20.0,30.0,50.0,60.0,500.0",
                    "2026-07-24 09:32,200.0,10.0,-10.0,40.0,80.0,600.0",
                ]
            }
        }
        _mock_requests_get(mock_em_get, payload)

        rows = eastmoney_fund_flow_minute("600519")
        assert mock_em_get.call_args.kwargs["params"]["secid"] == "1.600519"
        assert len(rows) == 2
        assert rows[0]["time"] == "2026-07-24 09:31"
        assert rows[0]["main_net"] == 100.0
        assert rows[0]["small_net"] == -20.0
        assert rows[0]["mid_net"] == 30.0
        assert rows[0]["large_net"] == 50.0
        assert rows[0]["super_net"] == 60.0
        assert isinstance(rows[0]["main_net"], float)

    @patch("modules.a_stock_data_client._em_get")
    def test_minute_exception_returns_empty(self, mock_em_get):
        """请求异常 / _em_get 返回 None：均返回空列表不抛错"""
        mock_em_get.side_effect = requests.ConnectionError("boom")
        assert eastmoney_fund_flow_minute("600519") == []

        mock_em_get.side_effect = None
        mock_em_get.return_value = None
        assert eastmoney_fund_flow_minute("600519") == []

    @patch("modules.a_stock_data_client._em_get")
    def test_120d_normal(self, mock_em_get):
        """120 日日级：字段顺序 date/super/large/mid/small/main，SZ 代码 secid 前缀为 0."""
        payload = {
            "data": {"klines": ["2026-07-23,60.0,50.0,30.0,-20.0,100.0", "2026-07-24,80.0,40.0,20.0,10.0,200.0"]}
        }
        _mock_requests_get(mock_em_get, payload)

        rows = stock_fund_flow_120d("000001")
        assert mock_em_get.call_args.kwargs["params"]["secid"] == "0.000001"
        assert len(rows) == 2
        assert rows[0]["date"] == "2026-07-23"
        assert rows[0]["super_net"] == 60.0
        assert rows[0]["large_net"] == 50.0
        assert rows[0]["mid_net"] == 30.0
        assert rows[0]["small_net"] == -20.0
        assert rows[0]["main_net"] == 100.0

    @patch("modules.a_stock_data_client._em_get")
    def test_120d_exception_returns_empty(self, mock_em_get):
        """请求异常返回空列表不抛错"""
        mock_em_get.side_effect = TimeoutError("timeout")
        assert stock_fund_flow_120d("000001") == []


# ==================== mootdx 通达信 K 线 ====================


class TestMootdxKline:
    """mootdx (通达信 TCP) K 线备用数据源"""

    def test_not_installed_returns_none(self, monkeypatch):
        """mootdx 未安装（ImportError）时返回 None 不抛错"""
        monkeypatch.setitem(sys.modules, "mootdx", None)
        monkeypatch.setitem(sys.modules, "mootdx.quotes", None)
        assert _mootdx_kline("600519") is None

    def test_bestip_first(self, monkeypatch):
        """优先 bestip=True 自动选优（替代 8 个服务器的顺序探测）"""
        mock_quotes_cls, _ = _install_fake_mootdx(monkeypatch, _make_tdx_bars())

        df = _mootdx_kline("600519", days=10)
        mock_quotes_cls.factory.assert_called_once_with(market="std", bestip=True)
        assert df is not None
        assert len(df) == 10

    def test_bestip_fail_fallback_default(self, monkeypatch):
        """bestip 探测失败：回退到默认 factory"""
        mock_quotes_cls, _ = _install_fake_mootdx(monkeypatch, _make_tdx_bars())
        mock_quotes_cls.factory.side_effect = [OSError("bestip failed"), mock_quotes_cls.factory.return_value]

        df = _mootdx_kline("600519", days=10)
        assert mock_quotes_cls.factory.call_count == 2
        assert mock_quotes_cls.factory.call_args_list[0].kwargs == {"market": "std", "bestip": True}
        assert mock_quotes_cls.factory.call_args_list[1].args == ()
        assert mock_quotes_cls.factory.call_args_list[1].kwargs == {"market": "std"}
        assert df is not None

    def test_kline_dataframe_mapping(self, monkeypatch):
        """datetime 映射为 8 位 trade_date（.str[:8] 按字符截取），pct_chg 自动计算，行数不丢失"""
        _install_fake_mootdx(monkeypatch, _make_tdx_bars(10))

        df = _mootdx_kline("600519", days=10)
        assert df is not None
        # 回归：旧实现 [:8] 按行切片会把 10 行截成 8 行，且日期残留时分秒
        assert len(df) == 10
        assert df["trade_date"].tolist()[:2] == ["20260720", "20260721"]
        assert all(len(str(d)) == 8 for d in df["trade_date"])
        assert "pct_chg" in df.columns
        assert df["pct_chg"].iloc[0] == 0.0

    def test_bars_none_or_empty_returns_none(self, monkeypatch):
        """bars 返回 None 或空 DataFrame 时返回 None"""
        mock_quotes_cls, mock_client = _install_fake_mootdx(monkeypatch, None)
        assert _mootdx_kline("600519") is None

        mock_client.bars.return_value = pd.DataFrame()
        assert _mootdx_kline("600519") is None

    def test_bars_exception_returns_none(self, monkeypatch):
        """bars 抛异常时返回 None 不抛错"""
        _, mock_client = _install_fake_mootdx(monkeypatch, None)
        mock_client.bars.side_effect = RuntimeError("tdx error")
        monkeypatch.setattr("socket.create_connection", MagicMock())
        assert _mootdx_kline("600519") is None


# ==================== AStockDataClient ====================


class TestAStockDataClient:
    """AStockDataClient 客户端方法（底层 HTTP 函数全部 mock）"""

    @pytest.fixture
    def client(self):
        c = AStockDataClient()
        c._min_interval = 0  # 测试时不限流
        return c

    # ---------- health_check ----------

    def test_health_check_success(self, client):
        """腾讯行情有结果时健康检查通过"""
        with patch("modules.a_stock_data_client.tencent_quote", return_value={"000001": _make_quote_dict()}):
            assert client.health_check() is True

    def test_health_check_failure(self, client):
        """异常或空结果时健康检查失败，不抛错"""
        with patch("modules.a_stock_data_client.tencent_quote", side_effect=ConnectionError("boom")):
            assert client.health_check() is False
        with patch("modules.a_stock_data_client.tencent_quote", return_value={}):
            assert client.health_check() is False

    # ---------- get_daily ----------

    def test_get_daily_baidu_path(self, client):
        """百度 K 线命中：补 ts_code 并按起止日期过滤"""
        with patch("modules.a_stock_data_client.baidu_kline_to_dataframe", return_value=_make_kline_df()):
            df = client.get_daily("600519.SH", "20260721", "20260722")
        assert df is not None
        assert len(df) == 2
        assert (df["ts_code"] == "600519.SH").all()
        assert df["trade_date"].tolist() == ["20260721", "20260722"]

    def test_get_daily_fallback_mootdx(self, client):
        """百度无数据时回退 mootdx"""
        with (
            patch("modules.a_stock_data_client.baidu_kline_to_dataframe", return_value=None),
            patch("modules.a_stock_data_client._mootdx_kline", return_value=_make_kline_df()),
        ):
            df = client.get_daily("600519.SH")
        assert df is not None
        assert len(df) == 3
        assert (df["ts_code"] == "600519.SH").all()

    def test_get_daily_baidu_exception_fallback(self, client):
        """百度解析抛异常时回退 mootdx，不向上抛错"""
        with (
            patch("modules.a_stock_data_client.baidu_kline_to_dataframe", side_effect=RuntimeError("解析失败")),
            patch("modules.a_stock_data_client._mootdx_kline", return_value=_make_kline_df()),
        ):
            df = client.get_daily("600519.SH")
        assert df is not None
        assert len(df) == 3

    def test_get_daily_all_fail_returns_none(self, client):
        """百度与 mootdx 都无数据时返回 None"""
        with (
            patch("modules.a_stock_data_client.baidu_kline_to_dataframe", return_value=None),
            patch("modules.a_stock_data_client._mootdx_kline", return_value=None),
        ):
            assert client.get_daily("600519.SH") is None

    def test_get_index_daily(self, client):
        """指数日线：百度 K 线 + 日期过滤；无数据返回 None"""
        with patch("modules.a_stock_data_client.baidu_kline_to_dataframe", return_value=_make_kline_df()):
            df = client.get_index_daily("000001.SH", "20260721", "20260722")
        assert df is not None
        assert len(df) == 2
        assert (df["ts_code"] == "000001.SH").all()

        with patch("modules.a_stock_data_client.baidu_kline_to_dataframe", return_value=None):
            assert client.get_index_daily("000001.SH") is None

    # ---------- get_realtime_quote ----------

    def test_get_realtime_quote(self, client):
        """实时快照：ts_code 转换、单位换算（万->元，亿->元）"""
        with patch("modules.a_stock_data_client.tencent_quote", return_value={"600519": _make_quote_dict()}) as mock_q:
            df = client.get_realtime_quote(["600519.SH"])
        mock_q.assert_called_once_with(["600519"])
        assert df is not None
        row = df.iloc[0]
        assert row["ts_code"] == "600519.SH"
        assert row["name"] == "贵州茅台"
        assert row["price"] == 1500.0
        assert row["vol"] == 500000.0 * 10000
        assert row["total_mv"] == 18843.0 * 1e8
        assert row["circ_mv"] == 18000.0 * 1e8
        assert row["turnover_rate"] == pytest.approx(1.23)

    def test_get_realtime_quote_empty_returns_none(self, client):
        """无行情结果返回 None；异常返回 None 不抛错"""
        with patch("modules.a_stock_data_client.tencent_quote", return_value={}):
            assert client.get_realtime_quote(["600519.SH"]) is None
        with patch("modules.a_stock_data_client.tencent_quote", side_effect=TimeoutError("timeout")):
            assert client.get_realtime_quote(["600519.SH"]) is None

    # ---------- get_moneyflow ----------

    def test_get_moneyflow(self, client):
        """分钟级资金流向聚合为单日汇总行"""
        rows = [
            {
                "time": "t1",
                "main_net": 100.0,
                "small_net": -20.0,
                "mid_net": 30.0,
                "large_net": 50.0,
                "super_net": 60.0,
            },
            {"time": "t2", "main_net": 200.0, "small_net": 10.0, "mid_net": -5.0, "large_net": 20.0, "super_net": 40.0},
        ]
        with patch("modules.a_stock_data_client.eastmoney_fund_flow_minute", return_value=rows):
            df = client.get_moneyflow("600519.SH", "20260724")
        assert df is not None
        row = df.iloc[0]
        assert row["ts_code"] == "600519.SH"
        assert row["trade_date"] == "20260724"
        assert row["net_mf_amount"] == 300.0
        # 输出 tushare 兼容列名（与 syncer.sync_moneyflow / moneyflow 表对齐）
        assert row["buy_sm_amount"] == -10.0
        assert row["buy_md_amount"] == 25.0
        assert row["buy_lg_amount"] == 70.0
        assert row["buy_elg_amount"] == 100.0
        assert row["net_mf_rate"] == 0.0

    def test_get_moneyflow_empty_returns_none(self, client):
        """无资金流向数据返回 None"""
        with patch("modules.a_stock_data_client.eastmoney_fund_flow_minute", return_value=[]):
            assert client.get_moneyflow("600519.SH", "20260724") is None

    # ---------- get_daily_basic ----------

    def test_get_daily_basic(self, client):
        """每日基础指标：pe/pb/市值字段映射"""
        with patch("modules.a_stock_data_client.tencent_quote", return_value={"600519": _make_quote_dict()}):
            df = client.get_daily_basic("600519.SH")
        assert df is not None
        row = df.iloc[0]
        assert row["ts_code"] == "600519.SH"
        assert row["pe"] == pytest.approx(26.1)
        assert row["pe_ttm"] == pytest.approx(25.6)
        assert row["pb"] == pytest.approx(8.5)
        assert row["total_mv"] == 18843.0 * 1e8

    def test_get_daily_basic_missing_code_returns_none(self, client):
        """行情结果中无该代码时返回 None"""
        with patch("modules.a_stock_data_client.tencent_quote", return_value={"000001": _make_quote_dict()}):
            assert client.get_daily_basic("600519.SH") is None

    # ---------- get_stock_basic ----------

    def test_get_stock_basic(self, client):
        """东财个股信息映射为 stock_basic 结构，6 开头为主板"""
        info = {
            "code": "600519",
            "name": "贵州茅台",
            "industry": "白酒",
            "total_shares": 1256197800,
            "float_shares": 1256197800,
            "mcap": 1.8e12,
            "float_mcap": 1.8e12,
            "list_date": "20010827",
            "price": 1500.0,
        }
        with patch("modules.a_stock_data_client.eastmoney_stock_info", return_value=info):
            df = client.get_stock_basic("600519.SH")
        assert df is not None
        row = df.iloc[0]
        assert row["ts_code"] == "600519.SH"
        assert row["name"] == "贵州茅台"
        assert row["industry"] == "白酒"
        assert row["market"] == "主板"
        assert row["list_date"] == "20010827"

    def test_get_stock_basic_kechuang_market(self, client):
        """688 开头应分类为科创板而非主板（回归：旧三元式顺序错误）"""
        info = {"code": "688981", "name": "中芯国际", "industry": "半导体"}
        with patch("modules.a_stock_data_client.eastmoney_stock_info", return_value=info):
            df = client.get_stock_basic("688981.SH")
        assert df is not None
        row = df.iloc[0]
        assert row["market"] == "科创板"

    def test_get_stock_basic_no_ts_code_returns_none(self, client):
        """全量查询不支持：不传 ts_code 时返回 None 且不调东财"""
        with patch("modules.a_stock_data_client.eastmoney_stock_info") as mock_info:
            assert client.get_stock_basic() is None
            mock_info.assert_not_called()

    # ---------- get_kline_dicts ----------

    def test_get_kline_dicts_sorted_and_limited(self, client):
        """K 线 dict 列表：按日期升序排序、days 截取尾部、数值为 float"""
        df = _make_kline_df(("20260722", "20260720", "20260721"))
        with patch.object(client, "get_daily", return_value=df):
            records = client.get_kline_dicts("600519.SH", days=2)
        assert [r["trade_date"] for r in records] == ["20260721", "20260722"]
        assert all(isinstance(r["close"], float) for r in records)
        assert all(r["ts_code"] == "600519.SH" for r in records)

    def test_get_kline_dicts_empty(self, client):
        """无 K 线数据时返回空列表"""
        with patch.object(client, "get_daily", return_value=None):
            assert client.get_kline_dicts("600519.SH") == []

    # ---------- 协议桩 ----------

    def test_protocol_stubs(self, client):
        """a-stock-data 不提供的接口：返回 None / 空列表"""
        assert client.get_stk_factor("600519.SH") is None
        assert client.get_trade_cal() is None
        assert client.get_stock_list() == []


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
