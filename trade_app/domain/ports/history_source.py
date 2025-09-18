from __future__ import annotations

from typing import Protocol

import pandas as pd


class HistorySourcePort(Protocol):
    """履歴ソースの抽象（MT5/CSV/API等）。I/Oは実装側に隔離。"""

    __responsibility__ = "履歴データ取得の抽象境界（barsをDataFrameで返す）"

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,  # 例: "m1","m5","h1","d1"
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame: ...
