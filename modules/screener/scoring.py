"""选股评分函数。"""

import logging

from ..indicators import calculate_ma
from ..indicators import calculate_kdj, calculate_bbi  # noqa: F401  re-export
from .data import _dict_to_daily

logger = logging.getLogger(__name__)


def calculate_vol_ma(vols: list[float], period: int) -> float:
    """计算量能均线（复用 calculate_ma 逻辑）"""
    return calculate_ma(vols, period)


def is_perfect_pattern(klines: list) -> tuple[bool, list[str]]:
    """
    判断是否完美图形

    完美图形条件:
    1. BBI之上
    2. 缩量整理
    3. 均线多头（可选）
    4. 非高位
    """
    if klines and isinstance(klines[0], dict):
        klines = _dict_to_daily(klines)

    if len(klines) < 30:
        return False, ["数据不足"]

    today = klines[-1]
    bbi = calculate_bbi(klines)
    closes = [k.close for k in klines]
    vols = [k.vol for k in klines]

    reasons = []
    warnings = []

    # 1. BBI之上
    if today.close > bbi:
        reasons.append("价格在BBI之上")
    else:
        warnings.append("价格在BBI下方")

    # 2. 缩量整理
    ma5_vol = calculate_vol_ma(vols, 5)
    today_vol = today.vol
    if today_vol < ma5_vol * 0.7:
        reasons.append("缩量整理")
    elif today_vol > ma5_vol * 1.5:
        warnings.append("放量突破，需观察")

    # 3. 均线多头
    ma5 = calculate_ma(closes, 5)
    ma10 = calculate_ma(closes, 10)
    ma20 = calculate_ma(closes, 20)
    if ma5 > ma10 > ma20:
        reasons.append("均线多头排列")
    elif ma5 < ma10:
        warnings.append("均线空头")

    # 4. 非高位（距历史高点跌幅充分）
    max_high = max(k.high for k in klines[-60:])
    drop_ratio = (max_high - today.close) / max_high
    if drop_ratio > 0.3:
        reasons.append(f"相对高点回调{drop_ratio * 100:.0f}%")
    elif drop_ratio < 0.1:
        warnings.append("接近历史高位")

    # 综合判断
    is_perfect = len(reasons) >= 2 and len(warnings) == 0

    return is_perfect, reasons


def score_b1_opportunity(klines: list) -> tuple[float, list[str]]:
    """
    评估B1买点机会（P3：融入沙漏评分因子）

    返回: (评分0-100, 原因列表)
    """
    if klines and isinstance(klines[0], dict):
        klines = _dict_to_daily(klines)

    if len(klines) < 20:
        return 0, ["数据不足"]

    today = klines[-1]
    k, d, j = calculate_kdj(klines)
    bbi = calculate_bbi(klines)
    closes = [k.close for k in klines]
    vols = [k.vol for k in klines]

    score = 0
    reasons = []

    # J值评分（核心）
    if j < -15:
        score += 35
        reasons.append(f"J值极低: {j:.2f}")
    elif j < -10:
        score += 25
        reasons.append(f"J值低位: {j:.2f}")
    elif j < 0:
        score += 15
        reasons.append(f"J值: {j:.2f}")

    # 缩量回调加分
    if today.vol < calculate_vol_ma(vols, 5) * 0.6:
        score += 20
        reasons.append("缩量回调")

    # BBI下方（低位）
    if today.close < bbi:
        score += 15
        reasons.append("BBI下方低位")

    # 价格在合理区间
    ma20 = calculate_ma(closes, 20)
    ma60 = calculate_ma(closes, 60)
    if ma20 < today.close < ma60:
        score += 15
        reasons.append("中期均线区间")

    # ========== P3 升级：沙漏因子融入 B1 评分 ==========
    try:
        from ..indicators import calculate_sandglass_score

        sg = calculate_sandglass_score(klines)
        sg_factors = sg.get("factors", {})
        sg_score = sg.get("score", 0)

        # 沙漏"缩量收敛"增强 B1 缩量回调确认
        contraction = sg_factors.get("缩量收敛", 0)
        if contraction >= 12:
            score += 10
            reasons.append(f"沙漏·缩量收敛({contraction}分)")
        elif contraction >= 8:
            score += 5
            reasons.append(f"沙漏·缩量收敛({contraction}分)")

        # 沙漏"枢轴邻近"确认低位支撑
        pivot = sg_factors.get("枢轴邻近", 0)
        if pivot >= 16:
            score += 8
            reasons.append(f"沙漏·枢轴邻近({pivot}分)")
        elif pivot >= 12:
            score += 4
            reasons.append(f"沙漏·枢轴邻近({pivot}分)")

        # 沙漏完美图形（≥80分）额外确认
        if sg.get("is_perfect"):
            score += 15
            reasons.append(f"沙漏完美图形({sg_score}分)")
        elif sg_score >= 65:
            score += 5
            reasons.append(f"沙漏良好({sg_score}分)")
    except (KeyError, ValueError, AttributeError, TypeError, ArithmeticError) as e:
        # 沙漏因子失败不影响主评分；调用方仍以原 score/reasons 继续。
        logger.warning("[scoring] 沙漏因子计算失败，跳过加分: %s", e)
        pass

    # 风险提示
    if j > 0:
        score -= 10
    if today.close > bbi * 1.05:
        score -= 15

    return max(0, min(100, score)), reasons


def score_trend(klines: list) -> tuple[float, str]:
    """
    评估趋势

    返回: (评分0-100, 趋势方向)
    """
    if klines and isinstance(klines[0], dict):
        klines = _dict_to_daily(klines)

    if len(klines) < 20:
        return 50, "震荡"

    closes = [k.close for k in klines]
    today = klines[-1]
    bbi = calculate_bbi(klines)

    ma5 = calculate_ma(closes, 5)
    ma20 = calculate_ma(closes, 20)
    ma60 = calculate_ma(closes, 60)

    # 趋势判断
    if ma5 > ma20 > ma60 and today.close > bbi:
        direction = "上升"
        score = 80 if today.pct_chg > 0 else 70
    elif ma5 < ma20 < ma60 and today.close < bbi:
        direction = "下降"
        score = 30
    else:
        direction = "震荡"
        score = 50

    # 短期动能
    if len(klines) >= 5:
        recent_pct = sum(k.pct_chg for k in klines[-5:])
        if recent_pct > 10:
            score += 10
        elif recent_pct < -10:
            score -= 10

    # 牛绳理论
    try:
        from ..indicators import detect_bull_rope

        rope = detect_bull_rope(klines)
        if rope.get("status") == "牵牛":
            score = min(100, score + 10)
            direction += " 牵牛"
        elif rope.get("status") == "牛绳断":
            score = max(0, score - 20)
            direction += " 牛绳断"
        elif rope.get("status") == "金叉":
            score = min(100, score + 15)
            direction += " 牛绳金叉"
        elif rope.get("status") == "死叉":
            score = max(0, score - 25)
            direction += " 牛绳死叉"
    except (KeyError, ValueError, AttributeError, TypeError, ArithmeticError) as e:
        # 牛绳理论失败不影响趋势评分；调用方仍用基础趋势分数兜底。
        logger.warning("[scoring] 牛绳理论计算失败，跳过: %s", e)
        pass

    return max(0, min(100, score)), direction


def score_volume_pattern(klines: list) -> tuple[float, list[str]]:
    """
    评估量价形态（P3：接入量比战法 6 场景判定）
    """
    if klines and isinstance(klines[0], dict):
        klines = _dict_to_daily(klines)

    if len(klines) < 10:
        return 50, ["数据不足"]

    today = klines[-1]
    vols = [k.vol for k in klines]
    vol_ma5 = calculate_vol_ma(vols, 5)
    vol_ratio = today.vol / vol_ma5 if vol_ma5 > 0 else 1.0

    score = 50
    reasons = []

    # ========== P3 升级：量比战法 6 场景判定（优先于简单量比计算）==========
    try:
        from ..indicators import detect_volume_ratio_strategy

        vr = detect_volume_ratio_strategy(klines)
        scenario = vr.get("scenario", "")
        action = vr.get("action", "")

        if scenario == "超级攻击":
            score += 30
            reasons.append(f"量比战法·超级攻击(量比{vr['vol_ratio']})")
        elif scenario == "攻击日":
            score += 25
            reasons.append(f"量比战法·攻击日(量比{vr['vol_ratio']})")
        elif scenario == "单向拉升":
            score += 18
            reasons.append(f"量比战法·单向拉升(量比{vr['vol_ratio']})")
        elif scenario == "出货日":
            score -= 25
            reasons.append(f"量比战法·出货日(量比{vr['vol_ratio']})→出货嫌疑")
        elif scenario == "弱势日":
            score -= 15
            reasons.append(f"量比战法·弱势日(量比{vr['vol_ratio']})")
        elif scenario == "正常震荡":
            if action == "慢买逢低吸纳":
                score += 5
                reasons.append(f"量比战法·震荡吸筹(量比{vr['vol_ratio']})")
            else:
                reasons.append("量比战法·观望")
    except (KeyError, ValueError, AttributeError, TypeError, ArithmeticError) as e:
        # 量比战法失败 → 降级到简单量比计算；调用方已有降级分支承接。
        logger.warning("[scoring] 量比战法计算失败，降级到简单量比: %s", e)
        # 降级到简单量比计算
        if vol_ratio >= 2:
            score += 20
            reasons.append(f"倍量(量比{vol_ratio:.1f}x)")
        elif vol_ratio >= 1.5:
            score += 10
            reasons.append("放量")
        elif vol_ratio <= 0.5:
            score += 10
            reasons.append("缩量")
        else:
            score -= 5
            reasons.append("量能正常")

    # 涨跌配合（保留，作为量比战法的补充验证）
    if today.pct_chg > 3 and vol_ratio > 1.2:
        score += 15
        reasons.append("价涨量增(攻击形态)")
    elif today.pct_chg < -3 and vol_ratio > 1.2:
        score -= 15
        reasons.append("价跌量增(出货嫌疑)")

    return max(0, min(100, score)), reasons


def score_risk(klines: list) -> tuple[float, list[str]]:
    """
    评估风险
    """
    if klines and isinstance(klines[0], dict):
        klines = _dict_to_daily(klines)

    if len(klines) < 20:
        return 50, ["数据不足"]

    today = klines[-1]
    bbi = calculate_bbi(klines)

    score = 100  # 初始100分，越高越安全
    warnings = []

    # 高位风险
    max_high = max(k.high for k in klines[-60:])
    drop_ratio = (max_high - today.close) / max_high
    if drop_ratio < 0.1:
        score -= 30
        warnings.append("接近历史高位")
    elif drop_ratio < 0.2:
        score -= 15
        warnings.append("相对高位")

    # 跌破BBI风险
    if today.close < bbi:
        score -= 20
        warnings.append("跌破BBI")

    # 放量阴线风险
    for i in range(min(5, len(klines) - 1)):
        k = klines[-(i + 1)]
        prev = klines[-(i + 2)] if i < len(klines) - 2 else None
        if prev and k.close < prev.close and k.vol > prev.vol * 1.5:
            score -= 10
            warnings.append("近期有放量阴线")
            break

    # 连续下跌
    recent_3_drop = sum(1 for k in klines[-3:] if k.close < k.prev_close)
    if recent_3_drop >= 3:
        score -= 15
        warnings.append("连续3天下跌")

    # 蜈蚣图检测（呼吸紊乱 = 高风险）
    try:
        from ..indicators import detect_centipede_pattern

        centipede = detect_centipede_pattern(klines)
        if centipede.get("is_centipede"):
            score -= 30
            warnings.append(f"蜈蚣图({centipede['score']:.0f}分)")
            warnings.append("检测到蜈蚣图风险，建议观望")
    except (KeyError, ValueError, AttributeError, TypeError, ArithmeticError) as e:
        # 蜈蚣图检测失败不影响基础风险分；调用方仍以基础评分兜底。
        logger.warning("[scoring] 蜈蚣图检测失败，跳过加分: %s", e)
        pass

    return max(0, min(100, score)), warnings
