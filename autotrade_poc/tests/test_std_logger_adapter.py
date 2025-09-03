from __future__ import annotations

import logging

from autotrade_poc.infrastructure.adapters.std_logger_adapter import StdLoggerAdapter


def test_logger_does_not_duplicate_handlers() -> None:
    l1 = StdLoggerAdapter(name="autotrade_test")
    before = len(logging.getLogger("autotrade_test").handlers)
    l2 = StdLoggerAdapter(name="autotrade_test")  # 再初期化
    after = len(logging.getLogger("autotrade_test").handlers)
    assert after == before  # 2回初期化してもハンドラ数は増えない
