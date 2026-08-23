"""M4: except narrowing tests for screener/* + verify/* + strategies/* + self_optimizer/* + indicators/*"""

import sys

import pytest


class TestScreenerNoBareExcept:
    def test_criteria(self):
        import inspect
        from modules.screener import criteria

        assert "except Exception" not in inspect.getsource(criteria)

    def test_scoring(self):
        import inspect
        from modules.screener import scoring

        assert "except Exception" not in inspect.getsource(scoring)

    def test_engine(self):
        import inspect
        from modules.screener import engine

        assert "except Exception" not in inspect.getsource(engine)


class TestVerifyNoBareExcept:
    def test_pipeline(self):
        import inspect
        from modules.verify import pipeline

        assert "except Exception" not in inspect.getsource(pipeline)

    def test_pool(self):
        import inspect
        from modules.verify import pool

        assert "except Exception" not in inspect.getsource(pool)

    def test_scorer(self):
        import inspect
        from modules.verify import scorer

        assert "except Exception" not in inspect.getsource(scorer)

    def test_walk_forward(self):
        import inspect
        from modules.verify import walk_forward

        assert "except Exception" not in inspect.getsource(walk_forward)

    def test_portfolio_walk_forward(self):
        import inspect
        from modules.verify import portfolio_walk_forward

        assert "except Exception" not in inspect.getsource(portfolio_walk_forward)


class TestStrategiesAndIndicatorsNoBareExcept:
    def test_sell_signals(self):
        import inspect
        from modules.strategies import sell_signals

        assert "except Exception" not in inspect.getsource(sell_signals)

    def test_data_layer(self):
        import inspect
        from modules.indicators import data_layer

        assert "except Exception" not in inspect.getsource(data_layer)

    def test_kirin_detector(self):
        import inspect
        from modules.indicators import kirin_detector

        assert "except Exception" not in inspect.getsource(kirin_detector)


class TestSelfOptimizerNoBareExcept:
    def test_backtest_scorer(self):
        import inspect
        from modules.self_optimizer import backtest_scorer

        assert "except Exception" not in inspect.getsource(backtest_scorer)

    def test_param_registry(self):
        import inspect
        from modules.self_optimizer import param_registry

        assert "except Exception" not in inspect.getsource(param_registry)

    def test_reflex_blacklist(self):
        import inspect
        from modules.self_optimizer import reflex_blacklist

        assert "except Exception" not in inspect.getsource(reflex_blacklist)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
