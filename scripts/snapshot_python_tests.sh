#!/usr/bin/env bash
# 跑全套 Python 测试并把状态保存到 .m0_baseline.txt
# M0 退出前必须确认全绿。

set -euo pipefail
cd "$(dirname "$0")/.."

# 排除需外部凭证（realdata / TUSHARE_TOKEN）的测试
TEST_TARGETS=(
    tests/test_backtest.py
    tests/test_backtest_portfolio.py
    tests/test_backtest_six_step.py
    tests/test_backtest_scorer.py
    tests/test_simulator.py
    tests/test_verify_pipeline.py
    tests/test_verify_gates.py
    tests/test_verify_scorer.py
    tests/test_verify_walk_forward.py
    tests/test_screener.py
    tests/test_core.py
    tests/test_indicators.py
    tests/test_rust_compat.py
)

OUT=".m0_baseline.txt"
: > "$OUT"

for t in "${TEST_TARGETS[@]}"; do
    if [ -f "$t" ]; then
        echo "=== $t ===" | tee -a "$OUT"
        pytest "$t" -q --no-header -m "not realdata and not slow" 2>&1 | tee -a "$OUT" || true
    fi
done

echo
echo "Baseline saved to $OUT"
echo "Pass count:"
grep -oE '[0-9]+ passed' "$OUT" | awk '{s+=$1} END {print s}'
