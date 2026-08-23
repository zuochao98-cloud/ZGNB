"""
量价模式检测模块
"""

from typing import Any

from .core import (
    DailyData,
    TradeSignal,
    calculate_ma,
    calculate_bbi,
    calculate_kdj,
    calculate_macd,
    calculate_vol_ratio,
)
from .price_patterns import detect_volume_pattern, detect_macd_signals


def detect_volume_anomaly(klines: list[DailyData]) -> dict:
    """
    异动选股法检测

    核心：成交量突然放大 + 价随量升 + 位置（60日线附近或下方）

    分级：
    - 詹姆斯级：建仓波大开大合，放巨量、假阴真阳反包、阳线密集堆积
    - 徐杰级：仅一根放量阳线，量能没堆起来

    返回异动信息，供后续缩量回调时介入
    """
    result = {
        "is_yidong": False,
        "yidong_type": "",
        "yidong_vol_ratio": 0,
        "yidong_above_60d": False,
    }
    if len(klines) < 65:  # 需要60日均线数据
        return result

    today = klines[-1]
    prev = klines[-2] if len(klines) > 1 else None
    if not prev or prev.vol <= 0:
        return result

    # 量比检测：今日量 / 5日均量 >= 2.0
    avg_vol_5 = sum(klines[i].vol for i in range(max(1, len(klines) - 6), len(klines) - 1)) / 5
    vol_ratio = today.vol / avg_vol_5 if avg_vol_5 > 0 else 0

    if vol_ratio < 2.0:
        return result

    # 价随量升：收盘涨且不是滞涨（涨幅/量比合理）
    if today.pct_chg <= 0:
        return result

    # 位置检测：收盘价是否在60日线附近或下方
    closes_60 = [k.close for k in klines[-60:]]
    ma60 = sum(closes_60) / 60
    above_60d = today.close >= ma60 * 0.95  # 在60日线上下5%以内或上方

    result["yidong_vol_ratio"] = round(vol_ratio, 2)
    result["yidong_above_60d"] = above_60d

    # 判断异动等级
    # 詹姆斯级：量大 + 涨幅可观 + 有阳线堆积迹象
    if vol_ratio >= 3.0 and today.pct_chg >= 5:
        # 检查最近几天是否有阳线堆积
        red_count = sum(1 for k in klines[-5:] if k.close > k.open)
        if red_count >= 3:
            result["is_yidong"] = True
            result["yidong_type"] = "詹姆斯级"
            return result

    # 徐杰级：单根放量阳线
    if vol_ratio >= 2.0 and today.pct_chg >= 2:
        result["is_yidong"] = True
        result["yidong_type"] = "徐杰级"

    return result


def calculate_sell_score(klines: list[DailyData]) -> tuple[int, str, dict[str, bool]]:
    """
    计算防卖飞评分 V1.4（5分制）

    评分条件：
    1. 收盘涨？ +1
    2. BBI 没破？ +1
    3. 不是放量阴线？ +1
    4. 趋势还向上？ +1
    5. J 没死叉？ +1

    Returns:
        (评分, 满分描述, 明细字典)
    """
    if len(klines) < 2:
        return 3, "数据不足", {}

    today = klines[-1]
    yesterday = klines[-2]

    score = 5
    reasons = []
    items = {}

    # 1. 收盘涨？
    close_up = (
        today.close > today.prev_close if hasattr(today, "prev_close") and today.prev_close > 0 else today.pct_chg > 0
    )
    items["收盘上涨"] = close_up
    if not close_up:
        score -= 1
        reasons.append("收盘不涨")

    # 2. BBI 没破？
    if len(klines) >= 24:
        bbi = calculate_bbi(klines)
        bbi_ok = today.close >= bbi
        items["BBI支撑"] = bbi_ok
        if not bbi_ok:
            score -= 1
            reasons.append("跌破BBI")

    # 3. 不是放量阴线？
    vol_pattern = detect_volume_pattern(today, yesterday)
    not_bearish_vol = not vol_pattern["is_fangliang_yinxian"]
    items["非放量阴线"] = not_bearish_vol
    if not not_bearish_vol:
        score -= 1
        reasons.append("放量阴线")

    # 4. 趋势还向上？（用简单均线判断）
    if len(klines) >= 5:
        ma5_today = calculate_ma([k.close for k in klines[-5:]], 5)
        ma5_yesterday = calculate_ma([k.close for k in klines[-6:-1]], 5)
        trend_up = ma5_today > ma5_yesterday
        items["趋势向上"] = trend_up
        if not trend_up:
            score -= 1
            reasons.append("均线向下")

    # 5. J 没死叉？
    if len(klines) >= 9:
        k, d, j = calculate_kdj(klines)
        j_ok = j >= d or j < 80  # J没有从高位下穿
        items["KDJ未死叉"] = j_ok
        if not j_ok:
            score -= 1
            reasons.append("KDJ死叉")

    reason_str = "；".join(reasons) if reasons else "无扣分项"
    return score, reason_str, items


def detect_trade_signal(klines: list[DailyData]) -> TradeSignal:
    """
    检测交易信号（集成 MACD 一票否决权）

    Args:
        klines: K线数据（至少30天）

    Returns:
        信号类型
    """
    if len(klines) < 30:
        return TradeSignal.WATCH

    today = klines[-1]
    yesterday = klines[-2]

    # 计算当前指标
    k, d, j = calculate_kdj(klines)
    dif_list, dea_list, macd_list = calculate_macd(klines)
    macd_list[-1] if macd_list else 0

    # MACD 语料判断
    macd_signals = {}
    if dif_list and dea_list:
        macd_signals = detect_macd_signals(klines, dif_list, dea_list, macd_list)

    # === 一票否决权：MACD 说不能买 → 绝对不买 ===
    if macd_signals.get("macd_veto", False):
        return TradeSignal.WATCH

    if macd_signals.get("is_gold_fake", False):
        return TradeSignal.S1

    bbi = calculate_bbi(klines)
    vol_pattern = detect_volume_pattern(today, yesterday)

    # ========== 卖出信号检测 ==========

    # S1: 放量阴线（最高优先级）
    if vol_pattern["is_fangliang_yinxian"] and today.pct_chg < -3:
        return TradeSignal.S1

    if macd_signals.get("is_top_divergence", False):
        return TradeSignal.S2

    if macd_signals.get("is_bottom_divergence", False):
        return TradeSignal.B1

    if macd_signals.get("is_dead_fake", False):
        return TradeSignal.B2

    if j < -10 and vol_pattern["is_suoliang"]:
        return TradeSignal.B1

    # B2: B1后放量确认
    if j > -10 and j < 55:
        prev_j_list = []
        for i in range(2, min(10, len(klines))):
            pk, pd, pj = calculate_kdj(klines[:-i])
            prev_j_list.append(pj)

        if any(pj < -10 for pj in prev_j_list):
            if today.pct_chg > 4 and vol_pattern["is_beidou"]:
                return TradeSignal.B2

    if len(klines) >= 5:
        prev_2 = klines[-3]
        if prev_2.close < prev_2.open and prev_2.vol > klines[-4].vol * 1.5:
            if j < -5 and vol_pattern["is_suoliang"]:
                return TradeSignal.SB1

    if today.close > bbi and j > 0 and today.pct_chg > 0:
        return TradeSignal.HOLD

    return TradeSignal.WATCH


def detect_chuhuo_wushi(klines: list[DailyData]) -> dict:
    """
    主力出货五种经典方式识别

    来源：sell-discipline.md 3.15
    核心判断尺：涨多了之后的放量阴线。

    返回五种出货方式的检测结果，每种有独立置信度。
    """
    if len(klines) < 20:
        return {"total_score": 0, "patterns": []}

    today = klines[-1]
    recent_20 = klines[-20:]
    recent_10 = klines[-10:]
    recent_high = max(k.high for k in recent_20)
    min(k.low for k in recent_20)

    # 必须处于相对高位（当前 >= 近期高点 × 0.85）
    if today.close < recent_high * 0.85:
        return {"total_score": 0, "patterns": []}

    patterns: list[dict[str, Any]] = []
    vols = [k.vol for k in recent_20]
    avg_vol_5 = sum(vols[-5:]) / 5 if len(vols) >= 5 else sum(vols) / len(vols)
    max_vol_20 = max(vols)

    # ===== 方式一：加速后单日放天量大阴 =====
    # 前10天涨幅 > 20%，当天跌幅 > 5%，天量
    if len(klines) >= 10:
        price_10_days_ago = klines[-10].close
        up_pct_10 = (recent_high - price_10_days_ago) / price_10_days_ago if price_10_days_ago > 0 else 0
        is_tianliang = today.vol >= max_vol_20 * 0.8 or today.vol >= avg_vol_5 * 2
        if up_pct_10 > 0.20 and today.pct_chg < -5 and is_tianliang:
            patterns.append(
                {
                    "type": "方式一：加速后单日放天量大阴",
                    "confidence": 0.95,
                    "desc": f"10日涨{up_pct_10 * 100:.0f}%后，当天跌{abs(today.pct_chg):.1f}%，天量",
                }
            )

    # ===== 方式二：次高点巨量长阴 =====
    # 近5天创过新高，当天挑战高点失败，放量长阴
    high_5d = max(k.high for k in recent_10[:5]) if len(recent_10) >= 5 else recent_high
    is_near_high = today.high >= high_5d * 0.98
    is_big_yin = today.pct_chg < -3 and today.close < today.open
    is_juliang = today.vol >= klines[-2].vol * 1.5 if len(klines) >= 2 else False
    if is_near_high and is_big_yin and is_juliang:
        patterns.append(
            {
                "type": "方式二：次高点巨量长阴",
                "confidence": 0.90,
                "desc": f"挑战高点({high_5d:.2f})失败，放量长阴跌{abs(today.pct_chg):.1f}%",
            }
        )

    # ===== 方式三：阶梯放量下跌 =====
    # 连续3-5根阴线，成交量维持高位，价格阶梯跌
    consecutive_yin = 0
    for i in range(1, min(6, len(klines))):
        k = klines[-i]
        if k.close < k.open:  # 阴线
            consecutive_yin += 1
        else:
            break
    # 检查这N根阴线的量是否维持高位
    if consecutive_yin >= 3:
        yin_vols = [klines[-i].vol for i in range(1, consecutive_yin + 1)]
        yin_vol_avg = sum(yin_vols) / len(yin_vols)
        if yin_vol_avg >= avg_vol_5 * 1.2:
            patterns.append(
                {
                    "type": "方式三：阶梯放量下跌",
                    "confidence": 0.85,
                    "desc": f"连续{consecutive_yin}根阴线放量下跌，平均量{yin_vol_avg / avg_vol_5:.1f}倍",
                }
            )

    # ===== 方式四：双头双放量巨阴 =====
    # 近20天有两个相近高点，每个后都有放量阴线
    if len(recent_20) >= 10:
        highs = [(i, k.high) for i, k in enumerate(recent_20)]
        highs.sort(key=lambda x: x[1], reverse=True)
        top2 = highs[:2]
        if len(top2) == 2:
            h1_idx, h1 = top2[0]
            h2_idx, h2 = top2[1]
            # 两个高点差异 < 5%，且间隔至少3天
            if abs(h1 - h2) / h1 < 0.05 and abs(h1_idx - h2_idx) >= 3:
                # 检查每个高点后是否有放量阴线
                def has_fangliang_yinxian_after(idx) -> bool:
                    """检测 idx 之后 3 天内是否出现放量阴线（量 >= 5 日均量 1.3 倍）。"""
                    for j in range(idx + 1, min(idx + 4, len(recent_20))):
                        k = recent_20[j]
                        if k.close < k.open and k.vol >= avg_vol_5 * 1.3:
                            return True
                    return False

                if has_fangliang_yinxian_after(h1_idx) and has_fangliang_yinxian_after(h2_idx):
                    patterns.append(
                        {
                            "type": "方式四：双头双放量巨阴",
                            "confidence": 0.90,
                            "desc": f"双头({h1:.2f}/{h2:.2f})，均出现放量阴线",
                        }
                    )

    # ===== 方式五：顶部绿肥红瘦 =====
    # 近10天阴量 > 阳量 × 1.5
    yin_vol_total: float = 0.0
    yang_vol_total: float = 0.0
    for k in recent_10:
        if k.close < k.open:
            yin_vol_total += k.vol
        else:
            yang_vol_total += k.vol
    if yang_vol_total > 0 and yin_vol_total / yang_vol_total > 1.5:
        patterns.append(
            {
                "type": "方式五：顶部绿肥红瘦",
                "confidence": 0.80,
                "desc": f"近10天阴量/阳量={yin_vol_total / yang_vol_total:.1f}倍",
            }
        )

    # 总分 = 最高置信度 + 0.1 × (模式数 - 1)
    total_score = max([p["confidence"] for p in patterns], default=0.0)
    total_score += 0.1 * max(0, len(patterns) - 1)
    total_score = min(total_score, 1.0)

    return {"total_score": round(total_score, 2), "patterns": patterns, "is_selling": total_score >= 0.80}


def detect_volume_ratio_strategy(klines: list[DailyData]) -> dict:
    """
    量比战法引擎（B1+1日量比决策）

    来源：trading-core.md 3.6 量比战法
    核心：B1信号次日的量比决定操作策略。

    量比决策矩阵：
    | 量比      | 开盘情况       | 操作            |
    |-----------|---------------|-----------------|
    | < 10      | 正常/震荡日    | 慢买，逢低吸纳   |
    | < 10      | 急跌           | 跳过，不看       |
    | > 20      | 涨             | 立即买          |
    | > 20      | 暴跌           | 观望            |
    | 10-20     | 量价齐升       | 买              |
    | 10-20     | 低开-2%以下    | 观望            |
    | > 40      | 涨             | 瞬间买入(超级攻击)|

    注意：因无分钟级数据，量比使用日级别量比（当日量/5日均量）。

    Args:
        klines: K线数据（至少6天，用于计算5日均量）

    Returns:
        {
            "vol_ratio": float,          # 量比值
            "scenario": str,             # 场景: 攻击日/出货日/单向拉升/弱势日/正常震荡/超级攻击
            "action": str,               # 操作: 立即买/观望/慢买逢低吸纳/跳过不看
            "confidence": float,         # 置信度 0-1
            "note": str,                 # 解释说明
        }
    """
    # 默认返回
    default = {
        "vol_ratio": 0.0,
        "scenario": "正常震荡",
        "action": "观望",
        "confidence": 0.0,
        "note": "数据不足，无法判断",
    }
    if len(klines) < 6:
        return default

    # 复用核心层 calculate_vol_ratio
    vol_ratio = calculate_vol_ratio(klines)
    today = klines[-1]
    pct_chg = today.pct_chg

    # 低开幅度（相对于昨收）
    low_open_pct = 0.0
    if today.prev_close > 0:
        low_open_pct = (today.open - today.prev_close) / today.prev_close * 100

    # ===== 判断场景 =====

    # 超级攻击：量比 > 40 且涨
    if vol_ratio > 40 and pct_chg > 1:
        return {
            "vol_ratio": round(vol_ratio, 2),
            "scenario": "超级攻击",
            "action": "立即买",
            "confidence": 0.95,
            "note": f"量比{vol_ratio:.1f}极度放大，涨幅{pct_chg:.2f}%，盘中垂直拉升信号，瞬间买入",
        }

    # 攻击日：量比 > 20 且涨
    if vol_ratio > 20 and pct_chg > 1:
        return {
            "vol_ratio": round(vol_ratio, 2),
            "scenario": "攻击日",
            "action": "立即买",
            "confidence": 0.85,
            "note": f"量比{vol_ratio:.1f}大幅放量，涨幅{pct_chg:.2f}%，攻击日确认，立即买入",
        }

    # 出货日：量比 > 20 且暴跌
    if vol_ratio > 20 and pct_chg < -3:
        return {
            "vol_ratio": round(vol_ratio, 2),
            "scenario": "出货日",
            "action": "观望",
            "confidence": 0.80,
            "note": f"量比{vol_ratio:.1f}放天量，但跌幅{pct_chg:.2f}%，疑似主力出货，观望为主（除非盘中突破日内高点）",
        }

    # 单向拉升：量比 10-20 且量价齐升
    if 10 <= vol_ratio <= 20 and pct_chg > 0:
        return {
            "vol_ratio": round(vol_ratio, 2),
            "scenario": "单向拉升",
            "action": "慢买逢低吸纳",
            "confidence": 0.70,
            "note": f"量比{vol_ratio:.1f}温和放量，涨幅{pct_chg:.2f}%，量价齐升，单向拉升概率大",
        }

    # 弱势（10-20区间但低开）：量比 10-20 且低开 -2% 以下
    if 10 <= vol_ratio <= 20 and low_open_pct < -2:
        return {
            "vol_ratio": round(vol_ratio, 2),
            "scenario": "弱势日",
            "action": "观望",
            "confidence": 0.70,
            "note": f"量比{vol_ratio:.1f}放量但低开{low_open_pct:.2f}%，弱势信号，观望",
        }

    # 弱势日（量比 < 10 且急跌）
    if vol_ratio < 10 and pct_chg < -2:
        return {
            "vol_ratio": round(vol_ratio, 2),
            "scenario": "弱势日",
            "action": "跳过不看",
            "confidence": 0.75,
            "note": f"量比{vol_ratio:.1f}缩量，跌幅{pct_chg:.2f}%，弱势日，跳过不看",
        }

    # 正常震荡日：量比 < 10
    if vol_ratio < 10:
        return {
            "vol_ratio": round(vol_ratio, 2),
            "scenario": "正常震荡",
            "action": "慢买逢低吸纳",
            "confidence": 0.60,
            "note": f"量比{vol_ratio:.1f}正常水平，涨幅{pct_chg:.2f}%，震荡日逢低吸纳",
        }

    # 量比 > 20 但涨幅在 -3% ~ 1% 之间（中性放量）
    if vol_ratio > 20:
        return {
            "vol_ratio": round(vol_ratio, 2),
            "scenario": "出货日",
            "action": "观望",
            "confidence": 0.60,
            "note": f"量比{vol_ratio:.1f}大幅放量，但涨幅{pct_chg:.2f}%不明确，观望为主",
        }

    # 量比 10-20 但 pct_chg <= 0 且未低开（中性）
    return {
        "vol_ratio": round(vol_ratio, 2),
        "scenario": "正常震荡",
        "action": "观望",
        "confidence": 0.50,
        "note": f"量比{vol_ratio:.1f}，涨幅{pct_chg:.2f}%，信号不明确，建议观望",
    }


def detect_volume_attack(klines: list[DailyData]) -> dict:
    """
    量比攻击信号检测（单日强势信号）

    来源：knowledge/three-best-principles.md

    触发条件：
    - 量比 > 3（当日成交量 / 5日平均成交量）
    - 涨幅 > 2%

    Returns:
        {
            "is_attack": bool,       # 是否触发攻击信号
            "vol_ratio": float,      # 量比值
            "pct_chg": float,        # 涨幅百分比
            "confidence": float,     # 置信度
            "desc": str,             # 描述
        }
    """
    result = {
        "is_attack": False,
        "vol_ratio": 0.0,
        "pct_chg": 0.0,
        "confidence": 0.0,
        "desc": "",
    }

    if len(klines) < 6:
        return result

    today = klines[-1]

    # 计算量比：当日成交量 / 5日平均成交量
    avg_vol_5 = sum(k.vol for k in klines[-6:-1]) / 5
    if avg_vol_5 <= 0:
        return result

    vol_ratio = today.vol / avg_vol_5
    pct_chg = today.pct_chg

    if vol_ratio > 3 and pct_chg > 2:
        confidence = min(0.70 + (vol_ratio - 3) * 0.05 + (pct_chg - 2) * 0.03, 0.95)
        result = {
            "is_attack": True,
            "vol_ratio": round(vol_ratio, 2),
            "pct_chg": round(pct_chg, 2),
            "confidence": round(confidence, 2),
            "desc": f"量比攻击：量比{vol_ratio:.2f}涨幅{pct_chg:.1f}%，强势信号",
        }

    return result
