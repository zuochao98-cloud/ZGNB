"""report.py 专项测试 — StockAssessment / assess_watchlist / render / write"""

import os
import sqlite3
import pytest
from pathlib import Path
from modules.report import (
    StockAssessment,
    assess_watchlist,
    render_assessment,
    write_assessment,
    _fmt_pct,
    _fmt_opt,
    _above_below,
    _zge_comment,
    _classify_sector,
    _resolve_db_path,
    MACRO_SECTORS,
    _INDUSTRY_TO_SECTOR,
)


# ==================== 辅助工厂 ====================


def _make_assessment(**kwargs) -> StockAssessment:
    """构造 StockAssessment 测试对象，提供合理默认值"""
    defaults = dict(
        ts_code="600519.SH",
        code="600519",
        name="贵州茅台",
        industry="白酒",
        sector="消费/食品/农业",
        trade_date="20260115",
        close=1800.0,
        pct_chg=1.5,
        vol_ratio=1.2,
        ma5=1790.0,
        ma20=1750.0,
        ma60=1700.0,
        k=65.0,
        d=60.0,
        j=75.0,
        dif=5.0,
        dea=3.0,
        macd_hist=0.5,
        rsi6=55.0,
        rsi12=50.0,
        boll_mid=1750.0,
        boll_upper=1850.0,
        boll_lower=1650.0,
        signal="WATCH",
        signal_desc="观察",
        sell_score=0,
        brick_trend="NEUTRAL",
        pe=30.5,
        pb=8.0,
        has_indicator=True,
    )
    defaults.update(kwargs)
    return StockAssessment(**defaults)


def _init_test_db(db_path: str, ts_codes: list[str] | None = None):
    """初始化测试用 DB，写入 minimal stock_basic / indicator_cache / financial_data"""
    if ts_codes is None:
        ts_codes = ["600519.SH"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS stock_basic (
            ts_code TEXT PRIMARY KEY, name TEXT, industry TEXT
        );
        CREATE TABLE IF NOT EXISTS indicator_cache (
            ts_code TEXT, trade_date TEXT, close REAL, pct_chg REAL, vol_ratio REAL,
            ma5 REAL, ma20 REAL, ma60 REAL, k REAL, d REAL, j REAL,
            dif REAL, dea REAL, macd_hist REAL, rsi6 REAL, rsi12 REAL,
            boll_mid REAL, boll_upper REAL, boll_lower REAL,
            signal TEXT, signal_desc TEXT, sell_score INTEGER, brick_trend TEXT
        );
        CREATE TABLE IF NOT EXISTS financial_data (
            ts_code TEXT, end_date TEXT, pe REAL, pb REAL
        );
    """)
    for tc in ts_codes:
        name = "贵州茅台" if "600519" in tc else tc
        industry = "白酒" if "600519" in tc else "其他"
        conn.execute("INSERT OR REPLACE INTO stock_basic VALUES (?,?,?)", (tc, name, industry))
        conn.execute(
            "INSERT INTO indicator_cache VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                tc,
                "20260115",
                1800.0,
                1.5,
                1.2,
                1790,
                1750,
                1700,
                65,
                60,
                75,
                5,
                3,
                0.5,
                55,
                50,
                1750,
                1850,
                1650,
                "WATCH",
                "观察",
                0,
                "NEUTRAL",
            ),
        )
        conn.execute(
            "INSERT INTO financial_data VALUES (?,?,?,?)",
            (tc, "20251231", 30.5, 8.0),
        )
    conn.commit()
    conn.close()


# ==================== StockAssessment ====================


class TestStockAssessment:
    def test_default_values(self):
        a = StockAssessment(ts_code="600519.SH")
        assert a.code == ""
        assert a.close == 0
        assert a.has_indicator is False
        assert a.signal == "WATCH"

    def test_custom_values(self):
        a = _make_assessment(signal="B1", pe=12.0)
        assert a.signal == "B1"
        assert a.pe == 12.0
        assert a.has_indicator is True

    def test_has_indicator_flag(self):
        a1 = _make_assessment(has_indicator=True)
        a2 = _make_assessment(has_indicator=False)
        assert a1.has_indicator is True
        assert a2.has_indicator is False


# ==================== _fmt_pct / _fmt_opt / _above_below ====================


class TestFormatters:
    def test_fmt_pct_positive(self):
        assert _fmt_pct(3.5) == "+3.50%"

    def test_fmt_pct_negative(self):
        assert _fmt_pct(-2.1) == "-2.10%"

    def test_fmt_pct_none(self):
        assert _fmt_pct(None) == "N/A"

    def test_fmt_pct_zero(self):
        assert _fmt_pct(0.0) == "+0.00%"

    def test_fmt_opt_normal(self):
        assert _fmt_opt(3.14159) == "3.14"

    def test_fmt_opt_decimals(self):
        assert _fmt_opt(3.14159, decimals=3) == "3.142"

    def test_fmt_opt_suffix(self):
        assert _fmt_opt(55.0, suffix="%") == "55.00%"

    def test_fmt_opt_sign(self):
        assert _fmt_opt(0.5, sign=True) == "+0.50"

    def test_fmt_opt_none(self):
        assert _fmt_opt(None) == "N/A"

    def test_above_below_above(self):
        assert _above_below(1800, 1750) == "站上"

    def test_above_below_below(self):
        assert _above_below(1700, 1750) == "跌破"

    def test_above_below_equal(self):
        assert _above_below(1750, 1750) == "跌破"

    def test_above_below_none(self):
        assert _above_below(1800, None) == "N/A"

    def test_above_below_zero(self):
        assert _above_below(1800, 0) == "N/A"


# ==================== _classify_sector ====================


class TestClassifySector:
    def test_known_industry(self):
        assert _classify_sector("证券") == "券商/金融"
        assert _classify_sector("半导体") == "光通信/电子元器件"
        assert _classify_sector("白酒") == "其他"  # 白酒不在映射中

    def test_unknown_industry(self):
        assert _classify_sector("未知行业") == "其他"

    def test_empty_string(self):
        assert _classify_sector("") == "其他"


# ==================== _zge_comment ====================


class TestZgeComment:
    def test_b1_signal(self):
        a = _make_assessment(signal="B1")
        comments = _zge_comment(a)
        assert any("B1" in c for c in comments)

    def test_s2_signal(self):
        a = _make_assessment(signal="S2")
        comments = _zge_comment(a)
        assert any("S2" in c for c in comments)

    def test_hold_signal(self):
        a = _make_assessment(signal="HOLD")
        comments = _zge_comment(a)
        assert any("持有" in c for c in comments)

    def test_watch_signal(self):
        a = _make_assessment(signal="WATCH")
        comments = _zge_comment(a)
        assert any("观察" in c for c in comments)

    def test_rsi_oversold(self):
        a = _make_assessment(rsi6=15.0)
        comments = _zge_comment(a)
        assert any("超卖" in c for c in comments)

    def test_rsi_overbought(self):
        a = _make_assessment(rsi6=80.0)
        comments = _zge_comment(a)
        assert any("超买" in c for c in comments)

    def test_kdj_j_very_low(self):
        a = _make_assessment(j=10.0)
        comments = _zge_comment(a)
        assert any("J" in c and "极低" in c for c in comments)

    def test_below_all_mas(self):
        a = _make_assessment(close=1600.0, ma5=1790, ma20=1750, ma60=1700)
        comments = _zge_comment(a)
        assert any("所有均线下方" in c for c in comments)

    def test_above_all_mas(self):
        a = _make_assessment(close=1900.0, ma5=1790, ma20=1750, ma60=1700)
        comments = _zge_comment(a)
        assert any("所有均线上方" in c for c in comments)

    def test_macd_red_below_zero(self):
        a = _make_assessment(macd_hist=0.5, dif=-2.0)
        comments = _zge_comment(a)
        assert any("筑底" in c for c in comments)

    def test_pe_undervalued(self):
        a = _make_assessment(pe=10.0)
        comments = _zge_comment(a)
        assert any("低估" in c for c in comments)

    def test_pe_overvalued(self):
        a = _make_assessment(pe=150.0)
        comments = _zge_comment(a)
        assert any("估值偏高" in c for c in comments)


# ==================== render_assessment ====================


class TestRenderAssessment:
    def test_empty_list(self):
        text = render_assessment([])
        assert "股票总数: 0只" in text

    def test_with_indicator(self):
        a = _make_assessment()
        text = render_assessment([a])
        assert "贵州茅台" in text
        assert "600519" in text
        assert "第一部分" in text
        assert "第二部分" in text
        assert "第三部分" in text

    def test_without_indicator(self):
        a = _make_assessment(
            has_indicator=False,
            close=0,
            ma5=None,
            ma20=None,
            ma60=None,
            k=None,
            d=None,
            j=None,
            dif=None,
            dea=None,
            macd_hist=None,
            rsi6=None,
            rsi12=None,
            boll_mid=None,
            boll_upper=None,
            boll_lower=None,
            pe=None,
            pb=None,
        )
        text = render_assessment([a])
        assert "待同步" in text

    def test_custom_title(self):
        text = render_assessment([], title="自定义标题")
        assert "自定义标题" in text

    def test_signal_summary_table(self):
        a = _make_assessment(signal="B1", rsi6=25.0, j=10.0, macd_hist=0.3)
        text = render_assessment([a])
        assert "信号汇总" in text

    def test_sector_classification(self):
        a1 = _make_assessment(ts_code="600519.SH", name="茅台", sector="消费/食品/农业", industry="白酒")
        a2 = _make_assessment(
            ts_code="601318.SH",
            name="平安",
            sector="券商/金融",
            industry="保险",
            has_indicator=False,
            close=0,
            ma5=None,
            ma20=None,
            ma60=None,
            k=None,
            d=None,
            j=None,
            dif=None,
            dea=None,
            macd_hist=None,
            rsi6=None,
            rsi12=None,
            boll_mid=None,
            boll_upper=None,
            boll_lower=None,
            pe=None,
            pb=None,
        )
        text = render_assessment([a1, a2])
        assert "消费/食品/农业" in text
        assert "券商/金融" in text

    def test_b1_suggestion_in_output(self):
        a = _make_assessment(signal="B1")
        text = render_assessment([a])
        assert "B1买入信号" in text

    def test_s2_suggestion_in_output(self):
        a = _make_assessment(signal="S2")
        text = render_assessment([a])
        assert "S2卖出信号" in text


# ==================== write_assessment ====================


class TestWriteAssessment:
    def test_write_to_file(self, tmp_path):
        out = str(tmp_path / "test_report.md")
        a = _make_assessment()
        chars = write_assessment([a], out)
        assert chars > 0
        content = Path(out).read_text(encoding="utf-8")
        assert "贵州茅台" in content
        assert len(content) == chars

    def test_write_empty_list(self, tmp_path):
        out = str(tmp_path / "empty.md")
        write_assessment([], out)
        content = Path(out).read_text(encoding="utf-8")
        assert "股票总数: 0只" in content

    def test_returns_character_count(self, tmp_path):
        """返回值是字符数，不是字节数"""
        out = str(tmp_path / "test.md")
        a = _make_assessment(name="测试中文", code="000001")
        chars = write_assessment([a], out)
        content = Path(out).read_text(encoding="utf-8")
        assert chars == len(content)


# ==================== assess_watchlist ====================


class TestAssessWatchlist:
    def test_empty_codes(self, mock_env_for_tests, tmp_path):
        """空列表返回空"""
        db_path = str(tmp_path / "test.db")
        _init_test_db(db_path, [])
        result = assess_watchlist([], db_path=db_path)
        assert result == []

    def test_single_stock(self, mock_env_for_tests, tmp_path):
        db_path = str(tmp_path / "test.db")
        _init_test_db(db_path, ["600519.SH"])
        result = assess_watchlist(["600519.SH"], db_path=db_path)
        assert len(result) == 1
        assert result[0].ts_code == "600519.SH"
        assert result[0].name == "贵州茅台"
        assert result[0].has_indicator is True
        assert result[0].close == 1800.0

    def test_multiple_stocks(self, mock_env_for_tests, tmp_path):
        db_path = str(tmp_path / "test.db")
        _init_test_db(db_path, ["600519.SH", "000001.SZ"])
        result = assess_watchlist(["600519.SH", "000001.SZ"], db_path=db_path)
        assert len(result) == 2

    def test_missing_stock_no_indicator(self, mock_env_for_tests, tmp_path):
        """DB 中有 basic 但无 indicator → has_indicator=False"""
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE stock_basic (ts_code TEXT PRIMARY KEY, name TEXT, industry TEXT);
            CREATE TABLE indicator_cache (
                ts_code TEXT, trade_date TEXT, close REAL, pct_chg REAL, vol_ratio REAL,
                ma5 REAL, ma20 REAL, ma60 REAL, k REAL, d REAL, j REAL,
                dif REAL, dea REAL, macd_hist REAL, rsi6 REAL, rsi12 REAL,
                boll_mid REAL, boll_upper REAL, boll_lower REAL,
                signal TEXT, signal_desc TEXT, sell_score INTEGER, brick_trend TEXT
            );
            CREATE TABLE financial_data (ts_code TEXT, end_date TEXT, pe REAL, pb REAL);
        """)
        conn.execute("INSERT INTO stock_basic VALUES (?,?,?)", ("600519.SH", "贵州茅台", "白酒"))
        conn.commit()
        conn.close()

        result = assess_watchlist(["600519.SH"], db_path=db_path)
        assert len(result) == 1
        assert result[0].has_indicator is False

    def test_completely_unknown_stock(self, mock_env_for_tests, tmp_path):
        """DB 中无此股票 → 返回空 name/industry"""
        db_path = str(tmp_path / "test.db")
        _init_test_db(db_path, [])
        result = assess_watchlist(["999999.SZ"], db_path=db_path)
        assert len(result) == 1
        assert result[0].name == ""
        assert result[0].has_indicator is False


# ==================== MACRO_SECTORS ====================


class TestMacroSectors:
    def test_sector_count(self):
        assert len(MACRO_SECTORS) >= 14

    def test_industry_to_sector_mapping(self):
        assert _INDUSTRY_TO_SECTOR["证券"] == "券商/金融"
        assert _INDUSTRY_TO_SECTOR["半导体"] == "光通信/电子元器件"
        assert _INDUSTRY_TO_SECTOR["汽车配件"] == "汽车/汽配/智能驾驶"

    def test_other_sector_has_empty_list(self):
        assert MACRO_SECTORS["其他"] == []
