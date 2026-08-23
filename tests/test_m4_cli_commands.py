"""M4: except narrowing tests for cli_commands.py"""

import sys

import pytest


class TestCliCommandsDailyFallback:
    """daily workflow 各步骤失败时不影响整个流程"""

    def test_no_bare_exception_in_cli_commands(self):
        """M4: 所有 except Exception 已收窄"""
        import inspect

        from modules import cli_commands

        source = inspect.getsource(cli_commands)
        # 所有 except Exception 都已替换为 narrowed types
        bare_count = source.count("except Exception")
        # 允许 BLE001 注释的 except Exception（应已被收窄）
        assert bare_count == 0, f"Found {bare_count} bare except Exception in cli_commands.py"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
