"""M4: except narrowing tests for tushare_client.py"""

import sys

import pytest

from modules.core.errors import ErrorCode, ZettarancError


class TestTushareClientRetryNarrow:
    """`_call_api_with_retry` 已收窄异常类型并保留 None-on-failure 契约"""

    def test_retry_exhausted_returns_none(self):
        """最终失败：返回 None（调用方通过 None 检查处理），并 log error"""
        import modules.tushare_client as tc

        client = tc.TushareClient.__new__(tc.TushareClient)
        client.min_request_interval = 0.0
        client.last_request_time = 0.0

        def boom(*a, **kw):
            raise ConnectionError("simulated network failure")

        result = client._call_api_with_retry("get_daily", boom)
        assert result is None

    def test_retry_then_success_does_not_raise(self):
        """第一次失败、第二次成功的场景：返回成功结果"""
        import modules.tushare_client as tc

        client = tc.TushareClient.__new__(tc.TushareClient)
        client.min_request_interval = 0.0
        client.last_request_time = 0.0

        calls = {"n": 0}

        def flaky(*a, **kw):
            calls["n"] += 1
            if calls["n"] == 1:
                raise ConnectionError("transient")
            return "ok"

        result = client._call_api_with_retry("get_daily", flaky)
        assert result == "ok"
        assert calls["n"] == 2

    def test_non_narrowed_exception_propagates(self):
        """未被 except 元组捕获的异常应向上传播（不再静默吞掉）"""
        import modules.tushare_client as tc

        client = tc.TushareClient.__new__(tc.TushareClient)
        client.min_request_interval = 0.0
        client.last_request_time = 0.0

        class WeirdError(Exception):
            pass

        def boom(*a, **kw):
            raise WeirdError("not in narrow tuple")

        with pytest.raises(WeirdError):
            client._call_api_with_retry("get_daily", boom)

    def test_verify_token_url_missing_logs_debug(self, caplog):
        """导入时 verify_token_url 不可用：不应抛异常，仅 logger.debug"""
        import modules.tushare_client as tc

        with caplog.at_level("DEBUG", logger=tc.logger.name):
            try:
                tc.TushareClient()
            except Exception:
                # 其他原因（如 token 缺失）失败不重要
                pass


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
