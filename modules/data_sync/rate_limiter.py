"""Rate limiting infrastructure for data synchronization."""

import os
import time
import logging
import collections
import multiprocessing

from ..constants import RATE_LIMITER_WINDOW_BUFFER_S

logger = logging.getLogger(__name__)

# 并发同步线程数（4 个 sync_* 方法共用）
_MAX_SYNC_WORKERS = 5


# ==================== 模块级限流器（v2.10.0 P1-4） ====================
# 多进程安全：同机多进程共享同一把 multiprocessing.Lock
# 限流仅同机多进程有效，跨机器需 Redis 协调（详见 plan P1-4 风险）
class _RateLimiter:
    """Tushare 限流器（多进程安全 + 滑动窗口 token bucket）

    设计：
    - 60s 滑动窗口内的请求计数（in-memory deque）
    - multiprocessing.Lock 序列化 critical section
    - TUSHARE_RPM env var 控制 max requests/min（默认 180，留 20 缓冲应对 200 上限）

    用法：
        _GLOBAL_LIMITER.wait()  # 阻塞直到安全可调
    """

    def __init__(self, max_per_min: int = 180) -> None:
        self._max = max_per_min
        self._window: collections.deque = collections.deque()
        # 关键：multiprocessing.Lock 不是进程间共享的默认锁
        # 在父进程创建，子进程 fork 后会继承一份
        self._lock = multiprocessing.Lock()

    def wait(self) -> None:
        """阻塞直到 60s 窗口内有空位"""
        with self._lock:
            now = time.monotonic()
            # 弹出 60s 外的旧时间戳
            while self._window and (now - self._window[0]) > 60:
                self._window.popleft()
            if len(self._window) >= self._max:
                # 等待最老一项出窗口
                sleep_for = 60 - (now - self._window[0]) + RATE_LIMITER_WINDOW_BUFFER_S  # 缓冲秒数
                logger.debug(f"限流：等 {sleep_for:.2f}s（窗口已满 {self._max} req）")
                time.sleep(sleep_for)
                # 重新弹出（防止极端情况）
                now = time.monotonic()
                while self._window and (now - self._window[0]) > 60:
                    self._window.popleft()
            self._window.append(time.monotonic())

    @property
    def current_count(self) -> int:
        """当前窗口内请求数（只读，调试用）"""
        with self._lock:
            now = time.monotonic()
            while self._window and (now - self._window[0]) > 60:
                self._window.popleft()
            return len(self._window)


# 模块级单例（v2.10.0 P1-4 替代原 instance-level _rate_limit_lock）
_GLOBAL_LIMITER = _RateLimiter(max_per_min=int(os.environ.get("TUSHARE_RPM", "180")))


def _rate_limit_global() -> None:
    """模块级公开限流入口（v2.10.0 P1-4 新增，替代 instance-level _rate_limit）"""
    _GLOBAL_LIMITER.wait()
