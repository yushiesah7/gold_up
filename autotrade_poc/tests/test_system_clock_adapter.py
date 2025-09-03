from __future__ import annotations

import time
from datetime import timedelta

from autotrade_poc.infrastructure.adapters.system_clock_adapter import SystemClockAdapter


def test_now_returns_timezone_aware() -> None:
    clk = SystemClockAdapter()
    now = clk.now()
    assert now.tzinfo is not None
    # UTC想定
    assert now.utcoffset() == timedelta(0)


def test_sleep_until_short_interval() -> None:
    clk = SystemClockAdapter()
    start = time.perf_counter()
    target = clk.now() + timedelta(seconds=0.10)
    clk.sleep_until(target)
    elapsed = time.perf_counter() - start
    assert elapsed >= 0.09
    assert elapsed < 1.0
