"""
Z哥量化评估报告生成模块（v2.10.0 重构自 scripts/generate_report.py）

设计目标：
- 业务逻辑（拉数据 + 算指标）下沉到 modules 层
- 脚本 scripts/generate_report.py 缩到 ~50 行薄壳
- markdown 模板集中维护，便于后续改版

公开 API：
- StockAssessment: 评估结果 dataclass
- assess_watchlist(ts_codes, conn=None) -> List[StockAssessment]
- render_assessment(assessments, title=...) -> str
- write_assessment(assessments, out_path) -> int  # 写入文件，返回字节数
"""

from __future__ import annotations
from typing import Optional

import os
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

# dotenv 加载已移至 modules/__init__.py


# ==================== 板块分类 ====================
# Z哥风格的"宏观板块"分类（从 generate_report.py 复刻，避免散落）
MACRO_SECTORS: dict[str, list[str]] = dict(
    [
        ("有色/贵金属/矿业", ["小金属", "铜", "黄金", "铝", "铅锌"]),
        ("光通信/电子元器件", ["通信设备", "元器件", "半导体", "IT设备"]),
        ("新能源/锂电/光伏", ["电气设备", "新型电力", "玻璃"]),
        ("汽车/汽配/智能驾驶", ["汽车配件", "汽车整车", "摩托车"]),
        ("军工/航天", ["航空"]),
        ("券商/金融", ["证券", "银行", "多元金融"]),
        ("医药/医疗", ["化学制药", "生物制药", "医疗保健", "中成药", "医药商业"]),
        ("化工/新材料", ["化工原料", "塑料", "化纤", "矿物制品", "染料涂料", "环境保护", "橡胶"]),
        ("机械/工程", ["专用机械", "工程机械", "机械基件", "化工机械", "建筑工程"]),
        ("科技/互联网/软件", ["软件服务", "互联网"]),
        ("消费/食品/农业", ["食品", "农业综合", "种植业", "饲料", "文教休闲", "造纸", "家用电器"]),
        ("建材/地产", ["其他建材", "区域地产"]),
        ("能源/电力", ["火力发电", "供气供热"]),
        ("物流/运输", ["水运", "仓储物流"]),
        ("其他", []),
    ]
)

_INDUSTRY_TO_SECTOR: dict[str, str] = {}
for _sector, _inds in MACRO_SECTORS.items():
    for _ind in _inds:
        _INDUSTRY_TO_SECTOR[_ind] = _sector


# ==================== 评估结果 ====================
@dataclass
class StockAssessment:
    """单只股票的评估结果（薄壳：含 analyze_stock + basic + financial）"""

    ts_code: str
    code: str = ""  # 6 位代码（无 .SH/.SZ）
    name: str = ""
    industry: str = ""
    sector: str = ""

    # 行情
    trade_date: str = ""
    close: float = 0
    pct_chg: float = 0
    vol_ratio: float = 0

    # 指标
    ma5: float | None = None
    ma20: float | None = None
    ma60: float | None = None
    k: float | None = None
    d: float | None = None
    j: float | None = None
    dif: float | None = None
    dea: float | None = None
    macd_hist: float | None = None
    rsi6: float | None = None
    rsi12: float | None = None
    boll_mid: float | None = None
    boll_upper: float | None = None
    boll_lower: float | None = None

    # 信号
    signal: str = "WATCH"
    signal_desc: str = ""
    sell_score: int = 0
    brick_trend: str = "NEUTRAL"

    # 估值
    pe: float | None = None
    pb: float | None = None

    has_indicator: bool = False  # True = 指标已计算；False = 仅有基本信息


# ==================== 数据加载 ====================
def _resolve_db_path() -> str:
    """统一从 DB_PATH env 读，fallback data/stock_data.db"""
    p = os.environ.get("DB_PATH")
    if p:
        return p
    return str(
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "stock_data.db",
        )
    )


def _classify_sector(industry: str) -> str:
    return _INDUSTRY_TO_SECTOR.get(industry, "其他")


def _build_assessments_from_db(
    ts_codes: list[str],
    conn: sqlite3.Connection,
) -> list[StockAssessment]:
    """
    从 DB 拉取 basic + financial + indicator_cache，组装 StockAssessment 列表
    不调用 analyze_stock（避免重复计算；调用方应已 sync_all_indicators）
    """
    if not ts_codes:
        return []

    placeholders = ",".join(["?"] * len(ts_codes))

    # basic
    cur = conn.cursor()
    cur.execute(
        f"SELECT ts_code, name, industry FROM stock_basic WHERE ts_code IN ({placeholders})",
        ts_codes,
    )
    basic = {row["ts_code"]: {"name": row["name"], "industry": row["industry"]} for row in cur.fetchall()}

    # financial（最新一条）
    cur.execute(
        f"""SELECT ts_code, pe, pb FROM financial_data WHERE ts_code IN ({placeholders})
            AND end_date = (SELECT MAX(end_date) FROM financial_data f2
                            WHERE f2.ts_code = financial_data.ts_code)""",
        ts_codes,
    )
    financial = {row["ts_code"]: {"pe": row["pe"], "pb": row["pb"]} for row in cur.fetchall()}

    # indicator_cache（最新一天）
    cur.execute(
        f"""SELECT ts_code, trade_date, close, pct_chg, vol_ratio,
                   ma5, ma20, ma60, k, d, j, dif, dea, macd_hist,
                   rsi6, rsi12, boll_mid, boll_upper, boll_lower,
                   signal, signal_desc, sell_score, brick_trend
            FROM indicator_cache
            WHERE ts_code IN ({placeholders})
              AND trade_date = (SELECT MAX(trade_date) FROM indicator_cache i2
                                WHERE i2.ts_code = indicator_cache.ts_code)""",
        ts_codes,
    )
    indicators = {row["ts_code"]: dict(row) for row in cur.fetchall()}

    assessments: list[StockAssessment] = []
    for tc in ts_codes:
        b = basic.get(tc, {})
        f = financial.get(tc, {})
        ind = indicators.get(tc)
        a = StockAssessment(
            ts_code=tc,
            code=tc.split(".")[0],
            name=b.get("name", ""),
            industry=b.get("industry", ""),
            sector=_classify_sector(b.get("industry", "")),
            pe=f.get("pe"),
            pb=f.get("pb"),
        )
        if ind:
            a.has_indicator = True
            a.trade_date = ind["trade_date"] or ""
            a.close = ind["close"] or 0
            a.pct_chg = ind["pct_chg"] or 0
            a.vol_ratio = ind["vol_ratio"] or 0
            a.ma5 = ind["ma5"]
            a.ma20 = ind["ma20"]
            a.ma60 = ind["ma60"]
            a.k = ind["k"]
            a.d = ind["d"]
            a.j = ind["j"]
            a.dif = ind["dif"]
            a.dea = ind["dea"]
            a.macd_hist = ind["macd_hist"]
            a.rsi6 = ind["rsi6"]
            a.rsi12 = ind["rsi12"]
            a.boll_mid = ind["boll_mid"]
            a.boll_upper = ind["boll_upper"]
            a.boll_lower = ind["boll_lower"]
            a.signal = ind["signal"] or "WATCH"
            a.signal_desc = ind["signal_desc"] or ""
            a.sell_score = ind["sell_score"] or 0
            a.brick_trend = ind["brick_trend"] or "NEUTRAL"
        assessments.append(a)
    return assessments


def assess_watchlist(
    ts_codes: list[str],
    db_path: str | None = None,
) -> list[StockAssessment]:
    """
    顶层 API：评估一组股票，返回 StockAssessment 列表

    调用方先确保 indicator_cache 表已 sync（用 DataSyncer.sync_all_indicators），
    本函数只读 DB 不计算。
    """
    db = db_path or _resolve_db_path()
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        return _build_assessments_from_db(ts_codes, conn)


# ==================== 文本格式化工具 ====================
def _fmt_pct(p: float | None) -> str:
    if p is None:
        return "N/A"
    return f"{p:+.2f}%"


def _fmt_opt(v: float | None, decimals: int = 2, suffix: str = "", sign: bool = False) -> str:
    if v is None:
        return "N/A"
    if sign:
        return f"{v:+.{decimals}f}{suffix}"
    return f"{v:.{decimals}f}{suffix}"


def _above_below(close: float, ma: float | None) -> str:
    if ma is None or ma == 0:
        return "N/A"
    if close > ma:
        return "站上"
    return "跌破"


def _zge_comment(a: StockAssessment) -> list[str]:
    """Z哥风格的自动点评（基于指标生成 1-N 条评论）"""
    comments = []
    if a.signal == "B1":
        comments.append("系统出现B1买入信号，值得关注")
    elif a.signal == "S2":
        comments.append("系统出现S2二级卖出信号，注意风险")
    elif a.signal == "HOLD":
        comments.append("强势持有中")
    else:
        comments.append("观察中，等待方向确认")

    if a.rsi6 is not None:
        if a.rsi6 < 20:
            comments.append(f"RSI={a.rsi6:.1f}极度超卖，短期可能反弹")
        elif a.rsi6 > 70:
            comments.append(f"RSI={a.rsi6:.1f}超买，警惕回调")
    if a.j is not None and a.j < 15:
        comments.append(f"KDJ-J={a.j:.1f}极低，短线反弹概率大")

    if a.ma5 and a.ma20 and a.ma60:
        if a.close < a.ma5 and a.close < a.ma20 and a.close < a.ma60:
            comments.append("股价在所有均线下方，趋势偏弱")
        elif a.close > a.ma5 and a.close > a.ma20 and a.close > a.ma60:
            comments.append("股价在所有均线上方，趋势偏强")
        elif a.close > a.ma5 and a.close > a.ma20 and a.close < a.ma60:
            comments.append("站上短中期均线，MA60压制需突破")

    if a.macd_hist is not None and a.dif is not None:
        if a.macd_hist > 0 and a.dif < 0:
            comments.append("MACD零轴下红柱，可能正在筑底")
    if a.pe is not None and 0 < a.pe < 15:
        comments.append(f"PE仅{a.pe:.1f}，低估有安全边际")
    elif a.pe is not None and a.pe > 100:
        comments.append(f"PE高达{a.pe:.1f}，估值偏高")

    return comments


# ==================== markdown 渲染 ====================
def render_assessment(assessments: list[StockAssessment], title: str = "Z哥量化评估报告 — 自选池深度扫描") -> str:
    """
    把 StockAssessment 列表渲染成 markdown 报告（3 部分：个股深度 + 板块概览 + 操作建议）
    """
    has_ind = sorted(
        [a for a in assessments if a.has_indicator],
        key=lambda x: x.name,
    )
    latest_date = has_ind[0].trade_date if has_ind else "N/A"
    total = len(assessments)
    n_ind = len(has_ind)

    L: list[str] = []
    L.append("=" * 80)
    L.append(f"  {title}")
    L.append("=" * 80)
    L.append("")
    L.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    L.append(f"数据截止: {latest_date}")
    L.append(f"股票总数: {total}只 | 完整量化指标: {n_ind}只")
    L.append("")
    L.append("核心原则:")
    L.append("  1. 先看大盘定仓位，再看板块选个股，最后战法找买卖点")
    L.append("  2. 好公司 != 好股票，好价格才是关键")
    L.append("  3. 量价不会骗人，指标滞后但确认")
    L.append("  4. 仓位管理比选股更重要")
    L.append("")

    # Part 1: 个股深度
    L.append("=" * 80)
    L.append(f"  第一部分：已有完整量化指标的股票（{n_ind}只深度分析）")
    L.append("=" * 80)
    L.append("")
    for a in has_ind:
        L.append("=" * 80)
        L.append(f"  {a.name} ({a.code})  [{a.industry}]")
        L.append("=" * 80)
        L.append("")

        ma5_s = _above_below(a.close, a.ma5)
        ma20_s = _above_below(a.close, a.ma20)
        ma60_s = _above_below(a.close, a.ma60)
        ma5_pct = _fmt_pct((a.close - a.ma5) / a.ma5 * 100) if a.ma5 and a.ma5 != 0 else "N/A"
        ma20_pct = _fmt_pct((a.close - a.ma20) / a.ma20 * 100) if a.ma20 and a.ma20 != 0 else "N/A"
        ma60_pct = _fmt_pct((a.close - a.ma60) / a.ma60 * 100) if a.ma60 and a.ma60 != 0 else "N/A"

        L.append("  【价格与均线】")
        L.append(f"    收盘价: {a.close:.2f}  涨跌: {a.pct_chg:+.2f}%  量比: {a.vol_ratio:.2f}")
        L.append(f"    MA5={_fmt_opt(a.ma5)} ({ma5_s} {ma5_pct})")
        L.append(f"    MA20={_fmt_opt(a.ma20)} ({ma20_s} {ma20_pct})")
        L.append(f"    MA60={_fmt_opt(a.ma60)} ({ma60_s} {ma60_pct})")
        L.append("")

        if a.j is not None:
            kdj_status = "超卖区" if a.j < 20 else ("超买区" if a.j > 80 else "中性区")
        else:
            kdj_status = "N/A"
        L.append(f"  【KDJ指标】K={_fmt_opt(a.k, 1)}  D={_fmt_opt(a.d, 1)}  J={_fmt_opt(a.j, 1)}  → {kdj_status}")
        L.append("")

        if a.macd_hist is not None:
            macd_dir = "红柱" if a.macd_hist > 0 else "绿柱"
        else:
            macd_dir = "N/A"
        if a.dif is not None and a.dea is not None:
            macd_cross = "多头" if a.dif > a.dea else "空头"
        else:
            macd_cross = "N/A"
        L.append(
            f"  【MACD指标】DIF={_fmt_opt(a.dif, 3)}  DEA={_fmt_opt(a.dea, 3)}  柱={_fmt_opt(a.macd_hist, 3, sign=True)} ({macd_dir} {macd_cross})"
        )
        L.append("")

        if a.rsi6 is not None:
            rsi_s = "超卖(<30)" if a.rsi6 < 30 else ("超买(>70)" if a.rsi6 > 70 else "中性")
        else:
            rsi_s = "N/A"
        L.append(f"  【RSI指标】RSI6={_fmt_opt(a.rsi6, 1)}  RSI12={_fmt_opt(a.rsi12, 1)}  → {rsi_s}")
        L.append("")

        L.append(f"  【系统信号】{a.signal} ({a.signal_desc})  卖出分={a.sell_score}/10  砖形={a.brick_trend}")
        pe_s = f"PE={a.pe:.1f}" if a.pe is not None else "PE=N/A"
        pb_s = f"PB={a.pb:.2f}" if a.pb is not None else "PB=N/A"
        L.append(f"  【估值】{pe_s}  {pb_s}")
        L.append("")

        L.append("  【Z哥点评】")
        for cm in _zge_comment(a):
            L.append(f"    · {cm}")
        L.append("")

    # 信号汇总表
    L.append("=" * 80)
    L.append("  信号汇总一览表")
    L.append("=" * 80)
    L.append("")
    L.append(
        f"{'名称':<10s} {'代码':<8s} {'收盘':>8s} {'涨跌':>8s} {'信号':<6s} {'RSI6':>6s} {'KDJ-J':>6s} {'MACD':>8s} {'砖形':<8s} {'PE':>6s}"
    )
    L.append("-" * 85)
    for s in sorted(has_ind, key=lambda x: x.signal):
        rsi = f"{s.rsi6:.1f}" if s.rsi6 is not None else "-"
        j = f"{s.j:.1f}" if s.j is not None else "-"
        macd = f"{s.macd_hist:+.3f}" if s.macd_hist is not None else "-"
        pe = f"{s.pe:.1f}" if s.pe is not None else "-"
        L.append(
            f"{s.name:<10s} {s.code:<8s} {s.close:>8.2f} {s.pct_chg:>+7.2f}% {s.signal:<6s} {rsi:>6s} {j:>6s} {macd:>8s} {s.brick_trend:<8s} {pe:>6s}"
        )
    L.append("")

    # Part 2: 板块概览
    L.append("=" * 80)
    L.append(f"  第二部分：自选池板块分类总览（共{total}只）")
    L.append("=" * 80)
    L.append("")

    sector_stocks: defaultdict[str, list[StockAssessment]] = defaultdict(list)
    for a in assessments:
        sector_stocks[a.sector].append(a)

    for sector, items in sector_stocks.items():
        items = sorted(items, key=lambda x: x.name)
        if not items and sector != "其他":
            continue
        n_ind_sector = sum(1 for s in items if s.has_indicator)
        L.append("=" * 80)
        L.append(f"  {sector} — {len(items)}只 (有指标: {n_ind_sector}只)")
        L.append("=" * 80)
        L.append("")

        sub_inds: defaultdict[str, int] = defaultdict(int)
        for s in items:
            sub_inds[s.industry] += 1
        if sub_inds:
            L.append("  【板块特征】")
            for sub, cnt in sorted(sub_inds.items(), key=lambda x: -x[1]):
                L.append(f"    {sub}: {cnt}只")
            L.append("")

        for s in items:
            pe_str = f"PE={s.pe:.1f}" if s.pe is not None else ""
            if s.has_indicator:
                if s.signal == "B1":
                    status = " ★B1"
                elif s.signal == "S2":
                    status = " ⚠S2"
                elif s.signal == "HOLD":
                    status = " ▲持有"
                else:
                    status = " ◉观察"
            else:
                status = " [待同步]"
            L.append(f"    {s.name:<10s} {s.code:<8s} {pe_str:<12s}{status}")
        L.append("")

    # Part 3: Z哥操作建议
    L.append("=" * 80)
    L.append("  第三部分：Z哥操作建议")
    L.append("=" * 80)
    L.append("")
    L.append("  已有量化信号的操作建议：")
    L.append("")

    for s in sorted(has_ind, key=lambda x: x.signal):
        name, code = s.name, s.code
        if s.signal == "B1":
            L.append(f"  ★ {name}({code}) — B1买入信号")
            pe_s = f"{s.pe:.1f}" if s.pe is not None else "N/A"
            rsi_s = f"{s.rsi6:.1f}" if s.rsi6 is not None else "N/A"
            macd_s = f"{s.macd_hist:+.3f}" if s.macd_hist is not None else "N/A"
            L.append(f"    PE={pe_s}, RSI={rsi_s}, MACD柱={macd_s}")
            if s.rsi6 is not None and s.rsi6 < 25:
                L.append("    极度超卖+买入信号共振，短线反弹概率大")
            if s.dif is not None and s.dif < 0 and s.macd_hist is not None and s.macd_hist > 0:
                L.append("    MACD零轴下方红柱，可能正在筑底")
            L.append("    建议：轻仓试多，设好止损，等放量确认")
        elif s.signal == "S2":
            L.append(f"  ⚠ {name}({code}) — S2卖出信号")
            L.append(
                f"    PE={s.pe if s.pe is not None else 'N/A'}, RSI={s.rsi6 if s.rsi6 is not None else 'N/A'}, 砖形={s.brick_trend}"
            )
            L.append("    建议：逢高减仓，落袋为安")
        elif s.signal == "HOLD":
            L.append(f"  ▲ {name}({code}) — 强势持有")
            L.append("    趋势向上，继续持有")
        else:
            L.append(f"  ◉ {name}({code}) — 观察中")
            L.append(f"    RSI={s.rsi6 if s.rsi6 is not None else 'N/A'}, KDJ-J={s.j if s.j is not None else 'N/A'}")
            if s.rsi6 is not None and s.rsi6 < 25:
                L.append("    超卖状态，等待止跌信号")
            L.append("    建议：等待方向确认后再决策")
        L.append("")

    L.append("=" * 80)
    L.append(f"  数据同步状态: {n_ind}/{total}只有完整量化指标")
    L.append("  后台数据同步仍在进行中（Tushare限流120次/分钟）")
    L.append("=" * 80)
    L.append("")
    L.append(f"--- 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')} ---")

    return "\n".join(L)


def write_assessment(assessments: list[StockAssessment], out_path: str) -> int:
    """渲染并写入文件，返回写入字符数"""
    content = render_assessment(assessments)
    with open(out_path, "w", encoding="utf-8") as f:
        chars_written = f.write(content)
    return chars_written
