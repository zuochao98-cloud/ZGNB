"""compat shim 的单元测试。"""

import importlib

import pytest


def test_default_is_rust(monkeypatch):
    monkeypatch.delenv("ZETTARANC_BACKTEST_IMPL", raising=False)
    from modules.core import _rust_compat

    importlib.reload(_rust_compat)
    assert _rust_compat.get_impl_choice() == "rust"


def test_invalid_impl_raises(monkeypatch):
    monkeypatch.setenv("ZETTARANC_BACKTEST_IMPL", "java")
    from modules.core import _rust_compat

    importlib.reload(_rust_compat)
    with pytest.raises(ValueError, match="invalid"):
        _rust_compat.get_impl_choice()


def test_python_choice_returns_none(monkeypatch):
    monkeypatch.setenv("ZETTARANC_BACKTEST_IMPL", "python")
    from modules.core import _rust_compat

    importlib.reload(_rust_compat)
    _rust_compat.reset_cache()
    assert _rust_compat.get_compute_module() is None


def test_rust_choice_returns_module(monkeypatch):
    pytest.importorskip("_core_compute", reason="_core_compute not built (run `maturin develop --release`)")
    monkeypatch.setenv("ZETTARANC_BACKTEST_IMPL", "rust")
    from modules.core import _rust_compat

    importlib.reload(_rust_compat)
    _rust_compat.reset_cache()
    mod = _rust_compat.get_compute_module()
    assert mod is not None
    assert mod.__name__ == "_core_compute"


def test_auto_mode_falls_back_on_import_error(monkeypatch):
    """auto 模式下如果 _core_compute 不存在应返回 None（不抛错）。"""
    monkeypatch.setenv("ZETTARANC_BACKTEST_IMPL", "auto")

    # 模拟 _core_compute 不可用
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "_core_compute":
            raise ImportError("simulated")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    from modules.core import _rust_compat

    importlib.reload(_rust_compat)
    _rust_compat.reset_cache()
    assert _rust_compat.get_compute_module() is None
