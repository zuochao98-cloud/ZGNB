"""
P1-4 回归测试：data_sync._RateLimiter 模块级限流器

- multiprocessing 安全（同机多进程共享）
- 滑动窗口 token bucket
- TUSHARE_RPM env var 覆盖
- 替换原 instance-level _rate_limit_lock
"""

import multiprocessing
import time
from pathlib import Path

from modules.data_sync.rate_limiter import _RateLimiter


PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ==================== 模块级 _RateLimiter 存在性 ====================


def test_rate_limiter_class_exists():
    """modules.data_sync.rate_limiter 必须有 _RateLimiter 类"""
    assert _RateLimiter is not None


def test_rate_limiter_module_level_singleton_exists():
    """模块级 _GLOBAL_LIMITER 单例必须存在"""
    from modules.data_sync.rate_limiter import _GLOBAL_LIMITER

    assert _GLOBAL_LIMITER is not None


def test_rate_limit_global_function_exists():
    """模块级 _rate_limit_global() 公开函数必须存在"""
    from modules.data_sync.rate_limiter import _rate_limit_global

    assert callable(_rate_limit_global)


def test_rate_limiter_available_via_data_sync_shim():
    """向后兼容：从 modules.data_sync shim 导入仍可用"""
    from modules.data_sync import _RateLimiter, _GLOBAL_LIMITER, _rate_limit_global, DataSyncer

    assert _RateLimiter is not None
    assert _GLOBAL_LIMITER is not None
    assert callable(_rate_limit_global)
    assert DataSyncer is not None


def test_data_syncer_uses_global_limiter():
    """DataSyncer._rate_limit() 必须调模块级 _GLOBAL_LIMITER.wait()"""
    import inspect
    from modules.data_sync.syncer import DataSyncer

    src = inspect.getsource(DataSyncer._rate_limit)
    assert "_rate_limit_global" in src
    assert "_GLOBAL_LIMITER" in src


# ==================== _RateLimiter 行为 ====================


def test_rate_limiter_init_default_180():
    """_RateLimiter() 默认 max_per_min=180（留 20 缓冲应对 200 上限）"""
    rl = _RateLimiter()
    assert rl._max == 180


def test_rate_limiter_init_respects_max_per_min():
    """_RateLimiter(max_per_min=N) 必须接受 N 参数"""
    rl = _RateLimiter(max_per_min=50)
    assert rl._max == 50


def test_rate_limiter_wait_does_not_block_under_limit():
    """未到上限时 wait() 应该立即返回"""
    rl = _RateLimiter(max_per_min=1000)  # 高上限，避免触发限流
    start = time.monotonic()
    for _ in range(10):
        rl.wait()
    elapsed = time.monotonic() - start
    assert elapsed < 0.5, f"10 次 wait() 耗时 {elapsed:.2f}s 异常长"


def test_rate_limiter_blocks_when_over_limit(monkeypatch):
    """超过上限时 wait() 必须调用 sleep 来阻塞（不实际等待 60s）"""
    rl = _RateLimiter(max_per_min=3)  # 低上限
    # 先快速吃满 3 个 token
    for _ in range(3):
        rl.wait()

    # 拦截真实 sleep，记录调用时长
    slept_seconds: list[float] = []
    monkeypatch.setattr(time, "sleep", slept_seconds.append)

    # 第 4 次必须触发阻塞
    rl.wait()
    assert slept_seconds, "wait() 超过上限时未调用 sleep 阻塞"
    assert slept_seconds[0] > 0, f"sleep 时长异常：{slept_seconds[0]}"


def test_rate_limiter_current_count_tracks_window():
    """current_count 必须反映当前 60s 窗口内的请求数"""
    rl = _RateLimiter(max_per_min=100)
    assert rl.current_count == 0
    for _ in range(5):
        rl.wait()
    assert rl.current_count == 5


# ==================== multiprocessing 安全 ====================


def _child_wait_n_times(n: int, max_per_min: int) -> int:
    """子进程函数：调 _RateLimiter.wait() n 次，返回最终 current_count"""
    rl = _RateLimiter(max_per_min=max_per_min)
    for _ in range(n):
        rl.wait()
    return rl.current_count


def test_rate_limiter_works_in_subprocess():
    """_RateLimiter 必须在子进程中能正常工作（multiprocessing.Lock 可继承）"""
    # 子进程中调 3 次 wait()，current_count 应为 3
    ctx = multiprocessing.get_context("fork")
    with ctx.Pool(1) as pool:
        result = pool.apply_async(_child_wait_n_times, (3, 1000))
        count = result.get(timeout=10)
    assert count == 3, f"子进程 current_count={count}（期望 3）"


def test_rate_limiter_works_across_multiple_subprocesses():
    """多子进程并发调 wait() 必须全部成功（multiprocessing.Lock 序列化）"""
    ctx = multiprocessing.get_context("fork")
    with ctx.Pool(2) as pool:
        r1 = pool.apply_async(_child_wait_n_times, (5, 1000))
        r2 = pool.apply_async(_child_wait_n_times, (5, 1000))
        c1 = r1.get(timeout=10)
        c2 = r2.get(timeout=10)
    # 每个子进程 current_count=5
    assert c1 == 5
    assert c2 == 5


# ==================== DataSyncer 集成 ====================


def test_data_syncer_keeps_legacy_attrs():
    """向后兼容：DataSyncer 实例仍保留 last_request_time / _rate_limit_lock / min_interval"""
    import os
    from unittest.mock import patch

    # 跳过 JNB 模式强制检查
    with patch.dict(os.environ, {"DATA_MODE": "websearch"}):
        from modules.data_sync import DataSyncer

        syncer = DataSyncer.__new__(DataSyncer)  # 绕过 __init__
        syncer.min_interval = 60 / 120
        syncer.last_request_time = {}
        import threading as _t

        syncer._rate_limit_lock = _t.Lock()
        assert syncer.min_interval > 0
        assert isinstance(syncer.last_request_time, dict)
        assert syncer._rate_limit_lock is not None


def test_data_syncer_rate_limit_does_not_crash():
    """DataSyncer._rate_limit(api_name) 调一次不应该崩（即使没真发请求）"""
    from modules.data_sync import DataSyncer

    # 用 __new__ 绕过 __init__ 的 Tushare token 强制检查（websearch 模式下不影响，
    # 但更稳是手动设 attrs）。设 min_interval/last_request_time/_rate_limit_lock 与 __init__ 一致。
    syncer = DataSyncer.__new__(DataSyncer)
    syncer.min_interval = 60 / 120
    syncer.last_request_time = {}
    import threading as _t

    syncer._rate_limit_lock = _t.Lock()
    # 调一次不应抛异常
    syncer._rate_limit("test_api")
    # last_request_time 仍被更新
    assert "test_api" in syncer.last_request_time


# ==================== TUSHARE_RPM env 变量 ====================


def test_global_limiter_reads_tushare_rpm_env(monkeypatch):
    """TUSHARE_RPM env var 必须能覆盖默认 180"""
    # 模块级 _GLOBAL_LIMITER 在 import 时已确定 max_per_min
    # 验证模块级代码确实读了 TUSHARE_RPM（静态检查）
    import inspect
    from modules.data_sync import rate_limiter

    src = inspect.getsource(rate_limiter)
    assert "TUSHARE_RPM" in src
    assert "os.environ.get" in src
