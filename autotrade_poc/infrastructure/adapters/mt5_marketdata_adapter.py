from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable
import time

import MetaTrader5 as mt5  # type: ignore

from autotrade_poc.ports.marketdata_port import MarketDataPort
from autotrade_poc.domain.models.market import Symbol, Timeframe
from autotrade_poc.domain.models.order import Bar


class MT5MarketDataAdapter(MarketDataPort):
    def latest_bar(self, symbol: Symbol, timeframe: Timeframe) -> Bar:
        _TIMEFRAME_MAP: dict[Timeframe, int] = {
            Timeframe.M1: mt5.TIMEFRAME_M1,
            Timeframe.M5: mt5.TIMEFRAME_M5,
            Timeframe.M15: mt5.TIMEFRAME_M15,
            Timeframe.M30: mt5.TIMEFRAME_M30,
            Timeframe.H1: mt5.TIMEFRAME_H1,
            Timeframe.H4: mt5.TIMEFRAME_H4,
            Timeframe.D1: mt5.TIMEFRAME_D1,
        }
        tf = _TIMEFRAME_MAP[timeframe]
        rates = mt5.copy_rates_from_pos(symbol.value, tf, 0, 1)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"copy_rates_from_pos failed: {mt5.last_error()}")
        r = rates[0]
        # MT5の time は epoch seconds（UTC）
        ts = datetime.fromtimestamp(int(r["time"]), tz=timezone.utc)
        return Bar(
            time=ts,
            open=float(r["open"]),
            high=float(r["high"]),
            low=float(r["low"]),
            close=float(r["close"]),
            volume=float(r["tick_volume"]),
        )

    def stream_bars(self, symbol: Symbol, timeframe: Timeframe) -> Iterable[Bar]:
        _TIMEFRAME_MAP: dict[Timeframe, int] = {
            Timeframe.M1: mt5.TIMEFRAME_M1,
            Timeframe.M5: mt5.TIMEFRAME_M5,
            Timeframe.M15: mt5.TIMEFRAME_M15,
            Timeframe.M30: mt5.TIMEFRAME_M30,
            Timeframe.H1: mt5.TIMEFRAME_H1,
            Timeframe.H4: mt5.TIMEFRAME_H4,
            Timeframe.D1: mt5.TIMEFRAME_D1,
        }
        tf = _TIMEFRAME_MAP[timeframe]
        last_ts: int | None = None
        while True:
            rates = mt5.copy_rates_from_pos(symbol.value, tf, 0, 2)
            if rates is None or len(rates) == 0:
                time.sleep(1.0)
                continue
            latest = rates[-1]
            ts_i = int(latest["time"])  # epoch seconds UTC
            if last_ts is None or ts_i > last_ts:
                last_ts = ts_i
                yield Bar(
                    time=datetime.fromtimestamp(ts_i, tz=timezone.utc),
                    open=float(latest["open"]),
                    high=float(latest["high"]),
                    low=float(latest["low"]),
                    close=float(latest["close"]),
                    volume=float(latest["tick_volume"]),
                )
            time.sleep(1.0)
