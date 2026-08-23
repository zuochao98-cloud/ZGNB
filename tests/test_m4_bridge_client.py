"""M4: except narrowing tests for bridge_client.py"""

import sys

import pytest

from modules.core.errors import ErrorCode


class TestBridgeClientFallback:
    """bridge_client 操作失败时按既有 fallback 返回（best-effort）"""

    def test_is_bridge_available_uses_narrow_exception(self, monkeypatch):
        """M4: 已收窄为 urllib.error.URLError/OSError/TimeoutError/JSON 异常等"""
        from modules import bridge_client as bc

        # 模拟 _http_get 抛 ConnectionError（在 OSError 子类树中，会被捕获）
        def boom(*a, **kw):
            raise ConnectionError("network down")

        monkeypatch.setattr(bc, "_http_get", boom)
        # OSError 子类会被捕获，best-effort 返回 False
        assert bc.is_bridge_available() is False

    def test_is_bridge_available_propagates_unrelated_error(self, monkeypatch):
        """未被窄化列表覆盖的异常应向上传播"""
        from modules import bridge_client as bc

        def boom(*a, **kw):
            raise RuntimeError("totally unexpected")

        monkeypatch.setattr(bc, "_http_get", boom)
        with pytest.raises(RuntimeError):
            bc.is_bridge_available()

    def test_get_bridge_daily_returns_empty_on_known_failure(self, monkeypatch):
        """模拟 urllib.error.URLError 时返回空列表（best-effort）"""
        import urllib.error

        from modules import bridge_client as bc

        def boom(*a, **kw):
            raise urllib.error.URLError("connection refused")

        monkeypatch.setattr(bc, "_http_get", boom)
        result = bc.get_bridge_daily("000001.SZ", days=30)
        assert result == []


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
