"""M4: except narrowing tests for simulator/* + commentary_service.py"""

import sys
import sqlite3

import pytest


class TestSimulatorMarketContextFallback:
    """market_context DB 读取失败时按 fallback 返回"""

    def test_no_silent_pass_in_market_context(self):
        """M4: 不应再出现 except Exception: pass"""
        import inspect

        from modules.simulator import market_context

        source = inspect.getsource(market_context)
        # 验证没有裸 except Exception: pass
        assert "except Exception:\n        pass" not in source


class TestSimulatorSignalFilterFallback:
    """signal_filter 失败时按 fallback 返回（best-effort）"""

    def test_no_silent_pass_in_signal_filter(self):
        import inspect

        from modules.simulator import signal_filter

        source = inspect.getsource(signal_filter)
        assert "except Exception:\n        pass" not in source


class TestCommentaryServiceFallback:
    """commentary_service 失败时按 fallback 返回（best-effort）"""

    def test_no_silent_pass_in_commentary(self):
        import inspect

        from modules import commentary_service

        source = inspect.getsource(commentary_service)
        assert "except Exception:\n        pass" not in source


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
