"""M4: except narrowing tests for llm_providers.py"""

import sys
import json

import pytest

from modules.core.errors import ErrorCode, ZettarancError


class TestLlmProvidersJsonDecodeNarrow:
    """`generate` 的 JSON 解析 except 已收窄为 JSONDecodeError, ValueError"""

    def test_json_decode_error_raises_zettaranc(self, monkeypatch):
        from modules import llm_providers as lp

        provider = lp.MiniMaxProvider.__new__(lp.MiniMaxProvider)
        provider.api_key = "fake"
        provider.base_url = "http://example.com/v1"
        provider.model = "fake-model"

        class FakeResp:
            status_code = 200

            def json(self):
                raise json.JSONDecodeError("bad json", "", 0)

            def raise_for_status(self):
                pass

        class FakeHttpx:
            @staticmethod
            def post(url, headers=None, json=None, timeout=None):
                return FakeResp()

        monkeypatch.setattr(lp, "httpx", FakeHttpx)
        with pytest.raises(ZettarancError) as exc_info:
            provider.generate("sys", "user")
        assert exc_info.value.code == ErrorCode.LLM_INVALID_RESPONSE


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
