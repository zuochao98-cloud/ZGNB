"""M4: except narrowing tests for watchlist.py + trade_parser.py + improvement_logger.py + indevs_client.py + cli.py"""

import sys

import pytest


class TestWatchlistNarrow:
    def test_no_bare_exception(self):
        import inspect
        from modules import watchlist

        assert "except Exception" not in inspect.getsource(watchlist)


class TestTradeParserNarrow:
    def test_no_bare_exception(self):
        import inspect
        from modules import trade_parser

        assert "except Exception" not in inspect.getsource(trade_parser)


class TestImprovementLoggerNarrow:
    def test_no_bare_exception(self):
        import inspect
        from modules import improvement_logger

        assert "except Exception" not in inspect.getsource(improvement_logger)


class TestIndevsClientNarrow:
    def test_no_bare_exception(self):
        import inspect
        from modules import indevs_client

        assert "except Exception" not in inspect.getsource(indevs_client)


class TestCliTopLevelNarrow:
    def test_no_bare_exception(self):
        import inspect
        from modules import cli

        assert "except Exception" not in inspect.getsource(cli)


class TestBacktestSixStepNarrow:
    def test_no_bare_exception(self):
        import inspect
        from modules import backtest_six_step

        assert "except Exception" not in inspect.getsource(backtest_six_step)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
