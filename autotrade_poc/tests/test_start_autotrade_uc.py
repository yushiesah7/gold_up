# -*- coding: utf-8 -*-
"""
Auto-generated tests for StartAutoTradeUC.

Testing framework: unittest (stdlib). These tests are also compatible with pytest discovery.
Scope: Validate the current public surface of StartAutoTradeUC based on the provided diff/skeleton:
- Proper dependency assignment in __init__
- run(...) is currently a no-op that returns None and performs no side effects
- Constructor enforces keyword-only arguments (star-args in signature)
"""

import unittest
from unittest.mock import Mock

# Flexible import strategy:
# 1) Try canonical package import
# 2) Fallback to dynamic import by locating the source file in the repo
try:
    from autotrade_poc.usecases.start_autotrade_uc import StartAutoTradeUC  # type: ignore
except Exception:
    import importlib.util as _ilu
    from pathlib import Path

    def _load_uc_class():
        repo_root = Path(__file__).resolve().parents[2]
        for p in repo_root.rglob("start_autotrade_uc.py"):
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if "class StartAutoTradeUC" in txt:
                spec = _ilu.spec_from_file_location("uc_mod_auto", p)
                mod = _ilu.module_from_spec(spec)
                assert spec.loader is not None
                spec.loader.exec_module(mod)
                return getattr(mod, "StartAutoTradeUC")
        raise ImportError("StartAutoTradeUC module not found")
    StartAutoTradeUC = _load_uc_class()


class TestStartAutoTradeUC(unittest.TestCase):
    def setUp(self):
        self.broker = Mock(name="BrokerPort")
        self.marketdata = Mock(name="MarketDataPort")
        self.clock = Mock(name="ClockPort")
        self.logger = Mock(name="LoggerPort")
        self.uc = StartAutoTradeUC(
            broker=self.broker,
            marketdata=self.marketdata,
            clock=self.clock,
            logger=self.logger,
        )

    def test_attributes_are_assigned(self):
        self.assertIs(self.uc.broker, self.broker)
        self.assertIs(self.uc.marketdata, self.marketdata)
        self.assertIs(self.uc.clock, self.clock)
        self.assertIs(self.uc.logger, self.logger)

    def test_run_returns_none_and_no_side_effects_on_empty_specs(self):
        result = self.uc.run([])
        self.assertIsNone(result)
        for m in (self.broker, self.marketdata, self.clock, self.logger):
            self.assertEqual(m.mock_calls, [])

    def test_run_is_noop_even_with_multiple_specs(self):
        specs = [object(), object()]
        result = self.uc.run(specs)
        self.assertIsNone(result)
        for m in (self.broker, self.marketdata, self.clock, self.logger):
            self.assertEqual(m.mock_calls, [])

    def test_constructor_enforces_keyword_only_args(self):
        # The constructor uses a '*' to enforce keyword-only parameters.
        with self.assertRaises(TypeError):
            StartAutoTradeUC(self.broker, self.marketdata, self.clock, self.logger)  # type: ignore[misc]

    def test_constructor_missing_dependency_raises(self):
        # Missing any required dependency should raise TypeError
        with self.assertRaises(TypeError):
            StartAutoTradeUC(marketdata=self.marketdata, clock=self.clock, logger=self.logger)  # type: ignore[call-arg]

    def test_run_accepts_tuple_sequence(self):
        result = self.uc.run((object(),))
        self.assertIsNone(result)
        for m in (self.broker, self.marketdata, self.clock, self.logger):
            self.assertEqual(m.mock_calls, [])


if __name__ == "__main__":
    unittest.main()