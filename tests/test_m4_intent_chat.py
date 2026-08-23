"""M4: except narrowing tests for intent_chat.py"""

import sys

import pytest

from modules.core.errors import ZettarancError


class TestIntentChatLlmFallback:
    """`get_llm` 在 LLM Provider 初始化失败时降级为 None，且不抛异常"""

    def test_get_llm_returns_none_when_provider_missing(self, monkeypatch):
        """Provider 类不存在时，get_llm 应返回 None（best-effort 降级）"""
        import modules.llm_providers as lp

        monkeypatch.setenv("LLM_API_KEY", "fake_key")

        # 强制让 MiniMaxProvider 构造抛异常
        class BoomProvider:
            def __init__(self, *a, **kw):
                raise ImportError("simulated provider failure")

        monkeypatch.setattr(lp, "MiniMaxProvider", BoomProvider)
        # get_llm 在内部 from .llm_providers import MiniMaxProvider，
        # 需重新 import 让 module-level binding 失效
        import importlib

        from modules import intent_chat

        importlib.reload(intent_chat)

        result = intent_chat.get_llm()
        assert result is None

    def test_get_llm_returns_none_when_no_key(self, monkeypatch):
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        from modules.intent_chat import get_llm

        assert get_llm() is None


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
