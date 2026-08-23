"""用 Python 计算与 Rust compute_atr 等价的滚动 ATR，生成 golden file。

Rust compute_atr 的语义：返回长度 = len(klines) 的 Vec<f64>，
前 (window-1) 个位置是 0.0，后续位置是 rolling mean of TR over window days。

本脚本用同样的 Python 实现生成 golden 数据，让 Rust 测试可以逐点比对。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def compute_atr_rolling(klines: list[dict], window: int) -> list[float]:
    """与 Rust compute_atr 等价的 Python 实现（用于生成 golden 数据）"""
    n = len(klines)
    if n < window:
        return []

    tr = [0.0] * n
    tr[0] = klines[0]["high"] - klines[0]["low"]
    for i in range(1, n):
        prev_close = klines[i - 1]["close"]
        hi = klines[i]["high"]
        lo = klines[i]["low"]
        range1 = hi - lo
        range2 = abs(hi - prev_close)
        range3 = abs(lo - prev_close)
        tr[i] = max(range1, range2, range3)

    atr = [0.0] * n
    s = 0.0
    for i in range(n):
        s += tr[i]
        if i >= window:
            s -= tr[i - window]
        if i + 1 >= window:
            atr[i] = s / window
    return atr


def make_synthetic_klines(n: int = 100, seed: int = 42) -> list[dict]:
    """生成合成 K 线，保证测试可重放。"""
    import random
    rng = random.Random(seed)
    price = 10.0
    rows = []
    for i in range(n):
        change = rng.uniform(-0.5, 0.5)
        price = max(0.1, price + change)
        high = price + rng.uniform(0, 0.3)
        low = price - rng.uniform(0, 0.3)
        rows.append({
            "ts_code": "TEST",
            "trade_date": i,
            "open": price,
            "high": high,
            "low": low,
            "close": price,
            "vol": rng.uniform(1e6, 1e7),
            "amount": rng.uniform(1e8, 1e9),
            "pct_chg": change / max(price, 0.01) * 100,
            "vol_ratio": rng.uniform(0.5, 2.0),
            "is_limit_up": False,
            "is_limit_down": False,
        })
    return rows


def main():
    out_dir = Path("tests/golden/atr")
    out_dir.mkdir(parents=True, exist_ok=True)

    cases = []
    for seed in (42, 7, 100):
        klines = make_synthetic_klines(100, seed=seed)
        for window in (14, 20):
            atr = compute_atr_rolling(klines, window=window)
            cases.append({
                "name": f"seed{seed}_w{window}",
                "input": klines,
                "window": window,
                "expected": atr,
            })

    out_file = out_dir / "basic.json"
    with out_file.open("w") as f:
        json.dump({"cases": cases}, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(cases)} cases to {out_file}")


if __name__ == "__main__":
    main()
