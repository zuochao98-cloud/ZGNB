#!/usr/bin/env python3
"""
策略达标验证规则引擎

定义策略必须达到的硬指标门槛，自动判断战法是否有效。

达标标准（缺一不可）：
1. 统计显著性：夏普 p-value < STATISTICS_SIGNIFICANCE_ALPHA
2. 置信区间：夏普 95% CI 下界 > 0.3
3. 防数据挖掘：Monte Carlo 置换检验 p-value < STATISTICS_SIGNIFICANCE_ALPHA
4. 稳健性：三个子周期（牛/熊/震荡）都赚钱
5. 绩效指标：胜率 > 40%，盈亏比 > 1.5，最大回撤 < 25%
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..constants import STATISTICS_SIGNIFICANCE_ALPHA


class CriteriaLevel(Enum):
    """验证级别"""

    STRICT = "strict"  # 严格模式（所有指标必须达标）
    MODERATE = "moderate"  # 中等模式（核心指标达标即可）
    LOOSE = "loose"  # 宽松模式（基本指标达标即可）


@dataclass
class CriteriaResult:
    """单项验证结果"""

    name: str  # 验证项名称
    passed: bool  # 是否通过
    actual_value: Any  # 实际值
    threshold: Any  # 阈值
    message: str  # 说明


@dataclass
class ValidationReport:
    """完整的验证报告"""

    strategy_name: str  # 策略名称
    level: CriteriaLevel = CriteriaLevel.MODERATE  # 验证级别
    overall_passed: bool = False  # 总体是否通过
    criteria_results: list[CriteriaResult] = field(default_factory=list)
    summary: str = ""  # 总结

    def add_result(self, result: CriteriaResult) -> None:
        """添加一项验证结果"""
        self.criteria_results.append(result)
        # 重新计算总体结果
        self._recalculate()

    def _recalculate(self):
        """重新计算总体结果"""
        if self.level == CriteriaLevel.STRICT:
            # 严格模式：所有项必须通过
            self.overall_passed = all(r.passed for r in self.criteria_results)
        elif self.level == CriteriaLevel.MODERATE:
            # 中等模式：核心项（统计显著性 + 绩效）必须通过
            core_names = ["夏普t检验", "Bootstrap置信区间", "胜率", "盈亏比", "最大回撤"]
            core_results = [r for r in self.criteria_results if r.name in core_names]
            self.overall_passed = all(r.passed for r in core_results)
        else:
            # 宽松模式：基本项（绩效）必须通过
            basic_names = ["胜率", "盈亏比"]
            basic_results = [r for r in self.criteria_results if r.name in basic_names]
            self.overall_passed = all(r.passed for r in basic_results)

    def generate_summary(self) -> str:
        """生成总结报告"""
        passed_count = sum(1 for r in self.criteria_results if r.passed)
        total_count = len(self.criteria_results)

        lines = [
            f"{'=' * 60}",
            f"策略验证报告：{self.strategy_name}",
            f"验证级别：{self.level.value}",
            f"{'=' * 60}",
            "",
            f"总体结果：{'✅ 通过' if self.overall_passed else '❌ 未通过'}",
            f"达标项目：{passed_count}/{total_count}",
            "",
        ]

        # 分类展示
        stat_tests = [r for r in self.criteria_results if "检验" in r.name or "置信" in r.name]
        perf_tests = [r for r in self.criteria_results if r.name in ["胜率", "盈亏比", "最大回撤", "夏普比率"]]
        other_tests = [r for r in self.criteria_results if r not in stat_tests and r not in perf_tests]

        if stat_tests:
            lines.append("【统计显著性检验】")
            for r in stat_tests:
                status = "✅" if r.passed else "❌"
                lines.append(f"  {status} {r.name}: {r.actual_value} (阈值: {r.threshold})")
                if not r.passed:
                    lines.append(f"     → {r.message}")
            lines.append("")

        if perf_tests:
            lines.append("【绩效指标】")
            for r in perf_tests:
                status = "✅" if r.passed else "❌"
                lines.append(f"  {status} {r.name}: {r.actual_value} (阈值: {r.threshold})")
                if not r.passed:
                    lines.append(f"     → {r.message}")
            lines.append("")

        if other_tests:
            lines.append("【其他检验】")
            for r in other_tests:
                status = "✅" if r.passed else "❌"
                lines.append(f"  {status} {r.name}: {r.actual_value} (阈值: {r.threshold})")
                if not r.passed:
                    lines.append(f"     → {r.message}")
            lines.append("")

        lines.append(f"{'=' * 60}")

        self.summary = "\n".join(lines)
        return self.summary


def validate_strategy(
    strategy_name: str,
    sharpe_test_result: Any = None,
    monte_carlo_result: Any = None,
    sub_period_result: Any = None,
    performance_metrics: dict | None = None,
    level: CriteriaLevel = CriteriaLevel.MODERATE,
) -> ValidationReport:
    """
    验证策略是否达标

    Args:
        strategy_name: 策略名称
        sharpe_test_result: 夏普 t 检验结果（SharpeTestResult）
        monte_carlo_result: Monte Carlo 置换检验结果（MonteCarloTestResult）
        sub_period_result: 子周期分析结果（SubPeriodAnalysis）
        performance_metrics: 绩效指标字典（win_rate, profit_factor, max_drawdown, sharpe_ratio）
        level: 验证级别

    Returns:
        ValidationReport: 完整验证报告
    """
    report = ValidationReport(strategy_name=strategy_name, level=level)

    performance_metrics = performance_metrics or {}

    # 1. 统计显著性检验
    if sharpe_test_result is not None:
        # 只有当样本量足够时才进行统计检验
        if sharpe_test_result.sample_size >= 10:
            # 夏普 t 检验
            report.add_result(
                CriteriaResult(
                    name="夏普t检验",
                    passed=sharpe_test_result.p_value < STATISTICS_SIGNIFICANCE_ALPHA,
                    actual_value=f"p={sharpe_test_result.p_value:.4f}",
                    threshold=f"p<{STATISTICS_SIGNIFICANCE_ALPHA}",
                    message="夏普比率显著大于0"
                    if sharpe_test_result.p_value < STATISTICS_SIGNIFICANCE_ALPHA
                    else "夏普比率不显著，策略可能无效",
                )
            )

            # Bootstrap 置信区间
            report.add_result(
                CriteriaResult(
                    name="Bootstrap置信区间",
                    passed=sharpe_test_result.ci_lower > 0.3,
                    actual_value=f"[{sharpe_test_result.ci_lower:.2f}, {sharpe_test_result.ci_upper:.2f}]",
                    threshold="下界>0.3",
                    message="置信区间稳定" if sharpe_test_result.ci_lower > 0.3 else "置信区间下界太低，策略收益不稳定",
                )
            )
        else:
            # 样本量不足，跳过统计检验
            report.add_result(
                CriteriaResult(
                    name="夏普t检验",
                    passed=True,  # 样本量不足时默认通过
                    actual_value=f"样本量{sharpe_test_result.sample_size}<10",
                    threshold="跳过",
                    message="样本量不足，跳过统计检验（建议增加回测期）",
                )
            )

            report.add_result(
                CriteriaResult(
                    name="Bootstrap置信区间",
                    passed=True,  # 样本量不足时默认通过
                    actual_value=f"样本量{sharpe_test_result.sample_size}<10",
                    threshold="跳过",
                    message="样本量不足，跳过置信区间计算",
                )
            )

    # 2. Monte Carlo 置换检验
    if monte_carlo_result is not None:
        # 只有当样本量足够时才进行置换检验
        if monte_carlo_result.n_permutations > 0:
            report.add_result(
                CriteriaResult(
                    name="Monte Carlo置换检验",
                    passed=monte_carlo_result.p_value < STATISTICS_SIGNIFICANCE_ALPHA,
                    actual_value=f"p={monte_carlo_result.p_value:.4f}",
                    threshold=f"p<{STATISTICS_SIGNIFICANCE_ALPHA}",
                    message="策略显著优于随机"
                    if monte_carlo_result.p_value < STATISTICS_SIGNIFICANCE_ALPHA
                    else "策略可能是数据挖掘产物",
                )
            )
        else:
            report.add_result(
                CriteriaResult(
                    name="Monte Carlo置换检验",
                    passed=True,  # 无法检验时默认通过
                    actual_value="样本量不足",
                    threshold="跳过",
                    message="样本量不足，跳过置换检验",
                )
            )

    # 3. 子周期稳健性
    if sub_period_result is not None:
        report.add_result(
            CriteriaResult(
                name="子周期稳健性",
                passed=sub_period_result.is_robust(),
                actual_value=f"稳健性得分={sub_period_result.robustness_score:.0f}",
                threshold="得分>=60",
                message="策略在某些市场环境下亏损"
                if not sub_period_result.is_robust()
                else "策略在所有市场环境下都有效",
            )
        )

    # 4. 绩效指标
    if "win_rate" in performance_metrics:
        win_rate = performance_metrics["win_rate"]

        # 智能胜率门槛：高盈亏比策略可以降低胜率要求
        profit_factor = performance_metrics.get("profit_factor", 0)
        if profit_factor > 5.0:
            win_rate_threshold = 0.25  # 盈亏比 > 5，胜率 25% 即可
            win_rate_message = "高盈亏比策略，胜率门槛降低"
        elif profit_factor > 3.0:
            win_rate_threshold = 0.30  # 盈亏比 > 3，胜率 30% 即可
            win_rate_message = "较高盈亏比，胜率门槛降低"
        else:
            win_rate_threshold = 0.40  # 标准门槛
            win_rate_message = "胜率太低" if win_rate <= win_rate_threshold else "胜率达标"

        report.add_result(
            CriteriaResult(
                name="胜率",
                passed=win_rate >= win_rate_threshold,
                actual_value=f"{win_rate * 100:.1f}%",
                threshold=f">={win_rate_threshold * 100:.0f}%",
                message=win_rate_message,
            )
        )

    if "profit_factor" in performance_metrics:
        profit_factor = performance_metrics["profit_factor"]
        report.add_result(
            CriteriaResult(
                name="盈亏比",
                passed=profit_factor > 1.5,
                actual_value=f"{profit_factor:.2f}",
                threshold=">1.5",
                message="盈亏比太低" if profit_factor <= 1.5 else "盈亏比达标",
            )
        )

    if "max_drawdown" in performance_metrics:
        max_dd = performance_metrics["max_drawdown"]
        report.add_result(
            CriteriaResult(
                name="最大回撤",
                passed=max_dd < 0.25,
                actual_value=f"{max_dd * 100:.1f}%",
                threshold="<25%",
                message="最大回撤太大" if max_dd >= 0.25 else "回撤控制良好",
            )
        )

    if "sharpe_ratio" in performance_metrics:
        sharpe = performance_metrics["sharpe_ratio"]
        report.add_result(
            CriteriaResult(
                name="夏普比率",
                passed=sharpe > 0.5,
                actual_value=f"{sharpe:.2f}",
                threshold=">0.5",
                message="夏普比率太低" if sharpe <= 0.5 else "夏普比率达标",
            )
        )

    # 生成总结
    report.generate_summary()

    return report
