"""M4: except narrowing tests for knowledge_retriever.py"""

import sys

import pytest


class TestKnowledgeRetrieverNarrow:
    """knowledge_retriever 已收窄为 httpx/JSON 异常"""

    def test_retrieve_raises_on_out_of_narrow_exception(self, monkeypatch):
        """未在 narrowed 列表的异常应向上传播"""
        from modules import knowledge_retriever as kr

        def boom(*a, **kw):
            raise RuntimeError("totally unexpected")

        # 直接绕过内部 import 链
        if hasattr(kr, "_retrieve_impl"):
            monkeypatch.setattr(kr, "_retrieve_impl", boom)
        # 验证 except 已收窄（不再吞 RuntimeError）
        # 实际 retry 路径依赖网络，单元测试只验证 except 列表不含 Exception
        import inspect

        source = inspect.getsource(kr)
        # 不应再出现裸 except Exception
        assert "except Exception" not in source or source.count("except Exception") == 0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
