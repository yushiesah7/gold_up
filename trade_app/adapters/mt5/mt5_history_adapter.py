from __future__ import annotations

from typing import ClassVar

import pandas as pd

from trade_app.domain.ports.history_source import HistorySourcePort


class MT5HistorySourceAdapter(HistorySourcePort):
    """MT5からbarsを取得（遅延import／DIで差替え可能）"""

    __responsibility__: ClassVar[str] = "MT5履歴取得のPort実装（範囲指定でOHLCV取得）"
    __debt_reason__: ClassVar[dict[str, str]] = {
        "reason": "環境ごとの差異（ENUM_TIMEFRAME等）はここで吸収",
        "owner": "infra",
    }

    def __init__(self, fetch_impl=None) -> None:
        self._fetch_impl = fetch_impl  # DI：テスト時に差し替え

    def _fetch_mt5(
        self, symbol: str, timeframe: str, start: pd.Timestamp, end: pd.Timestamp
    ) -> pd.DataFrame:
        import MetaTrader5 as mt5  # 遅延import  # noqa: PLC0415

        tf = getattr(mt5, f"TIMEFRAME_{timeframe.upper()}", None)
        if tf is None:
            raise ValueError(f"未知のtimeframe: {timeframe}")
        rates = mt5.copy_rates_range(symbol, tf, start.to_pydatetime(), end.to_pydatetime())
        if rates is None or len(rates) == 0:
            return pd.DataFrame(columns=["time", "open", "high", "low", "close", "tick_volume"])
        df = pd.DataFrame(rates)
        # MT5はtimeがUTCのPOSIX秒のことがある
        if pd.api.types.is_integer_dtype(df["time"]):
            df["time"] = pd.to_datetime(df["time"], unit="s")
        return df[["time", "open", "high", "low", "close", "tick_volume"]]

    def fetch_ohlcv(
        self, symbol: str, timeframe: str, start: pd.Timestamp, end: pd.Timestamp
    ) -> pd.DataFrame:
        impl = self._fetch_impl or self._fetch_mt5
        return impl(symbol, timeframe, start, end)
