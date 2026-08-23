"""M4: except narrowing tests for setup_wizard.py"""

import sys

import pytest

from modules.core.errors import ErrorCode, ZettarancError


class TestSetupWizardConnectionFallback:
    """`test_jnb_connection` 在连通性测试抛错时返回 False"""

    def test_returns_false_on_zettaranc_error(self, monkeypatch):
        import modules.tushare_client as tc
        from modules import setup_wizard as sw

        class FakeClient:
            def __init__(self, token):
                raise ZettarancError(ErrorCode.CONFIG_MISSING, "未配置")

            def check_connection(self):
                return True

        monkeypatch.setattr(tc, "TushareClient", FakeClient)
        assert sw.test_jnb_connection("any_token") is False

    def test_returns_false_on_os_error(self, monkeypatch):
        import modules.tushare_client as tc
        from modules import setup_wizard as sw

        class FakeClient:
            def __init__(self, token):
                raise OSError("network down")

            def check_connection(self):
                return True

        monkeypatch.setattr(tc, "TushareClient", FakeClient)
        assert sw.test_jnb_connection("any_token") is False


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
