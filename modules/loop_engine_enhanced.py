#!/usr/bin/env python3
"""
增强版少妇战法引擎

集成多个策略信号，通过投票机制提高胜率：
- B1（基础买点）
- B2（B1 后放量长阳确认）
- 长安战法（三日 B1）
- 娜娜图形（主升浪回踩）
- 平行重炮（双阳夹阴）

核心思想：
- 单一策略容易误判
- 多策略共振可以提高胜率
- 但会降低交易频率（需要权衡）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .loop_engine import ShaofuLoopEngine, LoopConfig, LoopTrade, LoopState
from .indicators import (
    DailyData,
    detect_b1_today,
    calculate_zg_white,
    calculate_dg_yellow,
)


@dataclass
class EnhancedLoopConfig(LoopConfig):
    """增强版配置"""

    # 策略集成配置
    enable_b2: bool = True  # 启用 B2 信号
    enable_changan: bool = True  # 启用长安战法
    enable_nana: bool = True  # 启用娜娜图形
    enable_pinghang: bool = True  # 启用平行重炮

    # 投票机制
    min_signals: int = 2  # 最少需要几个策略同意才入场
    signal_weights: dict[str, float] = field(
        default_factory=lambda: {
            "B1": 1.0,
            "B2": 1.2,  # B2 是确认信号，权重更高
            "长安": 1.5,  # 长安战法胜率高，权重最高
            "娜娜": 1.3,
            "平行重炮": 1.1,
        }
    )

    # 信号强度阈值
    min_signal_strength: float = 1.5  # 总信号强度阈值


@dataclass
class EnhancedLoopTrade(LoopTrade):
    """增强版交易记录"""

    triggered_strategies: list[str] = field(default_factory=list)  # 触发的策略列表
    signal_strength: float = 0.0  # 信号总强度


class EnhancedShaofuLoopEngine(ShaofuLoopEngine):
    """增强版少妇战法引擎"""

    def __init__(self, config: EnhancedLoopConfig | None = None) -> None:
        super().__init__(config or EnhancedLoopConfig())
        self.enhanced_config = config or EnhancedLoopConfig()

    def check_entry(self, klines: list[DailyData]) -> dict[str, Any] | None:
        """
        增强版入场检查

        集成多个策略信号，通过投票机制决定是否入场

        Args:
            klines: K 线数据

        Returns:
            信号字典或 None
        """
        if len(klines) < 30:
            return None

        # 1. 检测各个策略信号
        triggered_strategies = []
        signal_details = {}

        # B1 检测（基础）
        b1_result = self._detect_b1_enhanced(klines)
        if b1_result:
            triggered_strategies.append("B1")
            signal_details["B1"] = b1_result

        # B2 检测（可选）
        if self.enhanced_config.enable_b2:
            b2_result = self._detect_b2(klines)
            if b2_result:
                triggered_strategies.append("B2")
                signal_details["B2"] = b2_result

        # 长安战法检测（可选）
        if self.enhanced_config.enable_changan:
            changan_result = self._detect_changan(klines)
            if changan_result:
                triggered_strategies.append("长安")
                signal_details["长安"] = changan_result

        # 娜娜图形检测（可选）
        if self.enhanced_config.enable_nana:
            nana_result = self._detect_nana(klines)
            if nana_result:
                triggered_strategies.append("娜娜")
                signal_details["娜娜"] = nana_result

        # 平行重炮检测（可选）
        if self.enhanced_config.enable_pinghang:
            pinghang_result = self._detect_pinghang(klines)
            if pinghang_result:
                triggered_strategies.append("平行重炮")
                signal_details["平行重炮"] = pinghang_result

        # 2. 投票机制
        if len(triggered_strategies) < self.enhanced_config.min_signals:
            return None

        # 计算信号总强度
        total_strength = sum(self.enhanced_config.signal_weights.get(s, 1.0) for s in triggered_strategies)

        if total_strength < self.enhanced_config.min_signal_strength:
            return None

        # 3. 基础过滤（牛绳、缩量等）
        white = calculate_zg_white(klines)
        yellow = calculate_dg_yellow(klines)
        if white < yellow:
            return None

        today = klines[-1]

        # 4. 构建返回结果
        reason_parts = [
            f"策略共振: {', '.join(triggered_strategies)}",
            f"信号强度: {total_strength:.2f}",
        ]

        return {
            "is_b1": True,  # 兼容旧接口
            "j_value": b1_result.get("j_value", 50) if b1_result else 50,
            "entry_price": today.close,
            "signal": True,
            "reason": "增强B1: " + ", ".join(reason_parts),
            "triggered_strategies": triggered_strategies,
            "signal_strength": total_strength,
            "signal_details": signal_details,
        }

    def _detect_b1_enhanced(self, klines: list[DailyData]) -> dict[str, Any] | None:
        """增强版 B1 检测"""
        b1 = detect_b1_today(klines)
        if not b1.get("is_b1"):
            return None

        j_val = b1.get("b1_j_value", 50)
        if j_val > self.enhanced_config.j_threshold:
            return None

        # N 型上移结构
        n_structure_ok = self._check_n_structure(klines, len(klines) - 1)
        if not n_structure_ok:
            return None

        return {
            "j_value": j_val,
            "amplitude": b1.get("b1_amplitude", 0),
            "score": b1.get("b1_score", 0),
        }

    def _detect_b2(self, klines: list[DailyData]) -> dict[str, Any] | None:
        """
        B2 检测：B1 后放量长阳确认

        SOP: 前 5-15 日出现过 B1 + 当日放量长阳（涨幅≥4%）+ J值拐头
        """
        if len(klines) < 20:
            return None

        today = klines[-1]

        # 条件 1: 当日放量长阳（涨幅≥4%）
        if len(klines) < 2:
            return None
        yesterday = klines[-2]
        price_change = (today.close - yesterday.close) / yesterday.close if yesterday.close > 0 else 0
        if price_change < 0.04:  # 涨幅至少 4%
            return None

        # 条件 2: 放量（成交量 > 前日 1.5 倍）
        if yesterday.vol > 0 and today.vol < yesterday.vol * 1.5:
            return None

        # 条件 3: 近 5-15 日出现过 B1
        has_b1_recent = False
        for i in range(max(0, len(klines) - 15), len(klines) - 1):
            sub = klines[: i + 1]
            b1 = detect_b1_today(sub)
            if b1.get("is_b1"):
                has_b1_recent = True
                break

        if not has_b1_recent:
            return None

        return {
            "price_change": price_change,
            "volume_ratio": today.vol / yesterday.vol if yesterday.vol > 0 else 0,
        }

    def _detect_changan(self, klines: list[DailyData]) -> dict[str, Any] | None:
        """
        长安战法检测：三日 B1 + 放量阳 + 缩半量

        Day 1: J < -13 (B1) + Day 2: 放量长阳≥4% + Day 3: 小阳（0-2%）+ 缩半量
        """
        if len(klines) < 5:
            return None

        day2 = klines[-2]
        day3 = klines[-1]

        # Day 1: J < -13
        from .indicators import calculate_kdj

        kdj = calculate_kdj(klines[:-2])
        j_val = kdj[2] if isinstance(kdj, tuple) else kdj.j
        if j_val >= -13:
            return None

        # Day 2: 放量长阳≥4%
        if len(klines) < 4:
            return None
        day2_prev = klines[-4]
        day2_change = (day2.close - day2_prev.close) / day2_prev.close if day2_prev.close > 0 else 0
        if day2_change < 0.04:
            return None
        if day2.close < day2.open:  # 必须是阳线
            return None
        if day2_prev.vol > 0 and day2.vol < day2_prev.vol * 1.3:  # 放量
            return None

        # Day 3: 小阳（0-2%）+ 缩半量
        day3_change = (day3.close - day2.close) / day2.close if day2.close > 0 else 0
        if day3_change < 0 or day3_change > 0.02:
            return None
        if day3.close < day3.open:  # 必须是阳线
            return None
        if day2.vol > 0 and day3.vol > day2.vol * 0.6:  # 缩半量
            return None

        return {
            "day1_j": j_val,
            "day2_change": day2_change,
            "day3_change": day3_change,
        }

    def _detect_nana(self, klines: list[DailyData]) -> dict[str, Any] | None:
        """
        娜娜图形检测：放量涨 + 缩量回调 + J < 0

        3-5 日连续放量涨 + 顶部无巨量阴 + 2 日以上缩量回调 + J < 0
        """
        if len(klines) < 10:
            return None

        # 条件 1: J < 0
        from .indicators import calculate_kdj

        kdj = calculate_kdj(klines)
        j_val = kdj[2] if isinstance(kdj, tuple) else kdj.j
        if j_val >= 0:
            return None

        # 条件 2: 近 3-5 日有放量涨
        has_volume_up = False
        for i in range(max(0, len(klines) - 6), len(klines) - 2):
            day = klines[i]
            prev = klines[i - 1] if i > 0 else None
            if prev and day.close > prev.close and day.vol > prev.vol:
                has_volume_up = True
                break

        if not has_volume_up:
            return None

        # 条件 3: 近 2 日以上缩量回调
        shrink_days = 0
        for i in range(len(klines) - 3, len(klines) - 1):
            day = klines[i]
            prev = klines[i - 1] if i > 0 else None
            if prev and day.vol < prev.vol * 0.8:
                shrink_days += 1

        if shrink_days < 2:
            return None

        return {
            "j_value": j_val,
            "shrink_days": shrink_days,
        }

    def _detect_pinghang(self, klines: list[DailyData]) -> dict[str, Any] | None:
        """
        平行重炮检测：双阳夹阴

        两根放量阳线夹≥2 根阴线 + 阳线量能压阴线 1.2 倍 + 第二阳≥4% + J < 55
        """
        if len(klines) < 10:
            return None

        # 条件 1: J < 55
        from .indicators import calculate_kdj

        kdj = calculate_kdj(klines)
        j_val = kdj[2] if isinstance(kdj, tuple) else kdj.j
        if j_val >= 55:
            return None

        # 查找"双阳夹阴"形态
        # 简化实现：检查近 5 日是否有 阳-阴-阴-阳 或 阳-阴-阳 形态
        if len(klines) < 5:
            return None

        day1 = klines[-5]
        day2 = klines[-4]
        day3 = klines[-3]
        day4 = klines[-2]

        # 检查 阳-阴-阴-阳 形态
        is_yang1 = day1.close > day1.open
        is_yin2 = day2.close < day2.open
        is_yin3 = day3.close < day3.open
        is_yang4 = day4.close > day4.open

        if not (is_yang1 and is_yin2 and is_yin3 and is_yang4):
            return None

        # 检查第二阳涨幅≥4%
        day4_change = (day4.close - day3.close) / day3.close if day3.close > 0 else 0
        if day4_change < 0.04:
            return None

        # 检查阳线量能压阴线
        if day2.vol > 0 and day1.vol < day2.vol * 1.2:
            return None
        if day3.vol > 0 and day4.vol < day3.vol * 1.2:
            return None

        return {
            "j_value": j_val,
            "day4_change": day4_change,
        }

    def run_stock(self, klines: list[DailyData], ts_code: str = "") -> list[LoopTrade]:
        """
        对一只股票运行增强版六步闭环

        重写父类方法，使用增强版入场检查
        """
        trades: list[LoopTrade] = []
        current_trade: LoopTrade | None = None
        state = LoopState.TIMING

        for i in range(30, len(klines)):
            sub = klines[: i + 1]

            if state == LoopState.TIMING:
                # Step 1: 择时（白线在黄线上）
                white = calculate_zg_white(sub)
                yellow = calculate_dg_yellow(sub)
                if white >= yellow:
                    state = LoopState.WAITING_B1

            elif state == LoopState.WAITING_B1:
                # Step 3: 等 B1（增强版）
                signal = self.check_entry(sub)
                if signal:
                    # 入场
                    current_trade = LoopTrade(
                        ts_code=ts_code,
                        entry_date=klines[i].trade_date,
                        entry_price=signal["entry_price"],
                        entry_reason=signal["reason"],
                        stop_loss_price=self._calc_stop_loss(sub, signal["entry_price"]),
                    )

                    # 记录触发的策略
                    if hasattr(current_trade, "triggered_strategies"):
                        current_trade.triggered_strategies = signal.get("triggered_strategies", [])
                    if hasattr(current_trade, "signal_strength"):
                        current_trade.signal_strength = signal.get("signal_strength", 0.0)

                    state = LoopState.HOLDING

            elif state == LoopState.HOLDING:
                if current_trade is None:
                    state = LoopState.WAITING_B1
                    continue

                # Step 4: 止损检查
                if self._check_stop_loss_internal(klines, i, current_trade):
                    current_trade.exit_date = klines[i].trade_date
                    current_trade.exit_price = klines[i].close
                    current_trade.exit_reason = "止损"
                    current_trade.pnl_pct = self._calc_pnl_pct(current_trade)
                    current_trade.holding_days = i - klines.index(
                        next(k for k in klines if k.trade_date == current_trade.entry_date)
                    )
                    trades.append(current_trade)
                    current_trade = None
                    state = LoopState.WAITING_B1
                    continue

                # Step 5: 卤煮止盈
                if self._check_lu_zhu_internal(klines, i):
                    # 简化：减半仓（这里只记录，不实际减半）
                    pass

                # Step 6: 白线两日破位
                if self._check_white_line_exit_internal(klines, i):
                    current_trade.exit_date = klines[i].trade_date
                    current_trade.exit_price = klines[i].close
                    current_trade.exit_reason = "白线跌破"
                    current_trade.pnl_pct = self._calc_pnl_pct(current_trade)
                    current_trade.holding_days = i - klines.index(
                        next(k for k in klines if k.trade_date == current_trade.entry_date)
                    )
                    trades.append(current_trade)
                    current_trade = None
                    state = LoopState.WAITING_B1
                    continue

                # 白线死叉黄线（紧急离场）
                if self._check_dead_cross_exit(klines, i):
                    current_trade.exit_date = klines[i].trade_date
                    current_trade.exit_price = klines[i].close
                    current_trade.exit_reason = "白线死叉黄线"
                    current_trade.pnl_pct = self._calc_pnl_pct(current_trade)
                    current_trade.holding_days = i - klines.index(
                        next(k for k in klines if k.trade_date == current_trade.entry_date)
                    )
                    trades.append(current_trade)
                    current_trade = None
                    state = LoopState.WAITING_B1
                    continue

        return trades

    def _calc_stop_loss(self, klines: list[DailyData], entry_price: float) -> float:
        """计算止损价"""
        if self.enhanced_config.stop_loss_method == "entry_low":
            # 入场价 * (1 + 止损比例)
            return entry_price * (1 + self.enhanced_config.stop_loss_pct)
        else:
            # 其他方法（简化）
            return entry_price * 0.93

    def _calc_pnl_pct(self, trade: LoopTrade) -> float:
        """计算盈亏百分比"""
        if trade.entry_price > 0:
            return (trade.exit_price - trade.entry_price) / trade.entry_price * 100
        return 0.0
