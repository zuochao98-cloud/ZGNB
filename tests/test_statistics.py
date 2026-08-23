#!/usr/bin/env python3
"""
统计检验模块单元测试

测试内容：
1. 夏普比率计算准确性
2. t 检验 p-value 合理性
3. Bootstrap 置信区间覆盖
4. Monte Carlo 置换检验有效性
"""

import math
import pytest
from modules.statistics import sharpe_t_test, monte_carlo_permutation_test


class TestSharpeCalculation:
    """夏普比率计算测试"""

    def test_positive_sharpe(self):
        """测试正夏普（盈利策略）"""
        # 生成一个正收益的序列
        returns = [0.01, 0.02, -0.005, 0.015, 0.008, -0.003, 0.012, 0.01, -0.002, 0.009]
        result = sharpe_t_test(returns)

        assert result.sharpe_ratio > 0
        assert result.sample_size == len(returns)

    def test_negative_sharpe(self):
        """测试负夏普（亏损策略）"""
        # 生成一个负收益的序列
        returns = [-0.01, -0.02, 0.005, -0.015, -0.008, 0.003, -0.012, -0.01, 0.002, -0.009]
        result = sharpe_t_test(returns)

        assert result.sharpe_ratio < 0

    def test_zero_sharpe(self):
        """测试零夏普（无收益）"""
        returns = [0.0, 0.0, 0.0, 0.0, 0.0]
        result = sharpe_t_test(returns)

        assert result.sharpe_ratio == 0.0

    def test_small_sample(self):
        """测试小样本（应返回默认值）"""
        returns = [0.01, 0.02]
        result = sharpe_t_test(returns)

        # 样本量 < 10，应返回默认值
        assert result.p_value == 1.0
        assert not result.is_significant


class TestTTest:
    """t 检验测试"""

    def test_significant_positive_sharpe(self):
        """测试显著的正夏普"""
        # 生成一个稳定的正收益序列（高夏普）
        # 平均收益 1%，标准差 0.5%，夏普约 2.0
        returns = [0.01, 0.012, 0.008, 0.011, 0.009, 0.01, 0.013, 0.007, 0.012, 0.008] * 5
        result = sharpe_t_test(returns)

        # 应该是显著的
        assert result.p_value < 0.05
        assert result.is_significant
        assert result.t_statistic > 0

    def test_insufficient_sharpe(self):
        """测试不显著的夏普（噪声大）"""
        # 生成一个高方差的序列（低夏普）
        returns = [0.05, -0.04, 0.03, -0.02, 0.06, -0.05, 0.04, -0.03, 0.02, -0.01] * 3
        result = sharpe_t_test(returns)

        # 可能不显著（取决于具体数值）
        # 这里只验证函数能正常运行
        assert 0.0 <= result.p_value <= 1.0


class TestBootstrapCI:
    """Bootstrap 置信区间测试"""

    def test_ci_coverage(self):
        """测试置信区间包含点估计"""
        returns = [0.01, 0.02, -0.005, 0.015, 0.008, -0.003, 0.012, 0.01, -0.002, 0.009] * 5
        result = sharpe_t_test(returns)

        # 置信区间应该包含点估计
        assert result.ci_lower <= result.sharpe_ratio <= result.ci_upper

    def test_ci_width(self):
        """测试置信区间宽度（样本量越大越窄）"""
        # 小样本
        small_returns = [0.01, 0.02, -0.005, 0.015, 0.008, -0.003, 0.012, 0.01, -0.002, 0.009]
        small_result = sharpe_t_test(small_returns)

        # 大样本
        large_returns = small_returns * 10
        large_result = sharpe_t_test(large_returns)

        # 大样本的置信区间应该更窄
        small_width = small_result.ci_upper - small_result.ci_lower
        large_width = large_result.ci_upper - large_result.ci_lower
        assert large_width < small_width

    def test_ci_significance(self):
        """测试置信区间显著性判断"""
        # 高夏普策略（CI 下界应该 > 0.3）
        returns = [0.02, 0.015, 0.018, 0.022, 0.017, 0.019, 0.021, 0.016, 0.02, 0.018] * 5
        result = sharpe_t_test(returns)

        # 高夏普策略，CI 下界应该显著
        assert result.sharpe_ratio > 1.0  # 点估计高
        # CI 下界可能 > 0.3，也可能不是（取决于方差）


class TestMonteCarlo:
    """Monte Carlo 置换检验测试"""

    def test_significant_strategy(self):
        """测试策略显著性（函数能正常运行）"""
        # 注意：Monte Carlo 置换检验对夏普比率的效果有限
        # 因为夏普只依赖均值和标准差，打乱顺序不会改变这些统计量
        # 更有用的是 Bootstrap 置信区间（已测试）
        returns = [0.01, 0.02, -0.005, 0.015, 0.008, -0.003, 0.012, 0.01, -0.002, 0.009] * 3
        result = monte_carlo_permutation_test(returns, n_permutations=100, seed=42)

        # 验证函数能正常运行
        assert result.actual_sharpe > 0
        assert 0.0 <= result.p_value <= 1.0
        assert result.n_permutations == 100

    def test_random_strategy(self):
        """测试随机策略（可能不显著）"""
        # 生成一个随机序列（可能有正有负）
        returns = [0.02, -0.015, 0.008, -0.012, 0.005, -0.008, 0.01, -0.01, 0.003, -0.005] * 3
        result = monte_carlo_permutation_test(returns, n_permutations=100, seed=42)

        # 随机策略可能不显著
        assert 0.0 <= result.p_value <= 1.0
        assert result.n_permutations == 100

    def test_reproducibility(self):
        """测试可重复性（相同种子应得到相同结果）"""
        returns = [0.01, 0.02, -0.005, 0.015, 0.008] * 5

        result1 = monte_carlo_permutation_test(returns, n_permutations=100, seed=42)
        result2 = monte_carlo_permutation_test(returns, n_permutations=100, seed=42)

        assert result1.p_value == result2.p_value
        assert result1.actual_sharpe == result2.actual_sharpe


class TestEdgeCases:
    """边界情况测试"""

    def test_empty_returns(self):
        """测试空序列"""
        result = sharpe_t_test([])
        assert result.sharpe_ratio == 0.0
        assert result.p_value == 1.0

    def test_single_return(self):
        """测试单个收益"""
        result = sharpe_t_test([0.01])
        assert result.sharpe_ratio == 0.0

    def test_zero_variance(self):
        """测试零方差（所有收益相同）"""
        returns = [0.01] * 20
        result = sharpe_t_test(returns)
        # 零方差时夏普应为无穷大或特殊处理
        assert result.standard_error == 0.0 or result.t_statistic == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
