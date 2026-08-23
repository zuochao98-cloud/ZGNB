"""M4: except narrowing tests for notifier.py"""

import sys

import pytest


class TestNotifierFallback:
    """通知失败为 best-effort：返回 False 并记录日志，不抛 ZettarancError"""

    def test_notify_macos_returns_false_on_subprocess_error(self, monkeypatch):
        from modules import notifier

        # 模拟 subprocess.run 抛 CalledProcessError
        import subprocess

        def boom(*a, **kw):
            raise subprocess.CalledProcessError(1, "osascript")

        monkeypatch.setattr(notifier.subprocess, "run", boom)
        assert notifier.notify_macos("t", "m") is False

    def test_notify_macos_returns_false_on_file_not_found(self, monkeypatch):
        from modules import notifier

        import subprocess

        def boom(*a, **kw):
            raise FileNotFoundError("osascript not found")

        monkeypatch.setattr(notifier.subprocess, "run", boom)
        assert notifier.notify_macos("t", "m") is False

    def test_notify_feishu_returns_false_on_request_exception(self, monkeypatch):
        from modules import notifier
        import requests

        def boom(*a, **kw):
            raise requests.ConnectionError("network down")

        monkeypatch.setattr(notifier.requests, "post", boom)
        assert notifier.notify_feishu("http://example.com/hook", "t", "m") is False


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
