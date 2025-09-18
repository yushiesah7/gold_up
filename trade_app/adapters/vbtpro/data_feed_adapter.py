from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import ClassVar

import pandas as pd

from trade_app.adapters.vbtpro import vbtpro_bindings as vb
from trade_app.domain.dto.ohlcv_frame import OhlcvFrameDTO
from trade_app.domain.ports.data_feed import DataFeedPort
from trade_app.utils.timing import build_logger, time_phase


class VbtProDataFeedAdapter(DataFeedPort):
    """ParquetData.pull() 経由でOHLCVを取得（UTC awareを保証）"""

    __responsibility__: ClassVar[str] = "vbt PRO データ取得のPort実装"
    __debt_reason__: ClassVar[dict[str, str]] = {
        "reason": "本番ではvb.parquet_pullを実APIに差し替える",
        "owner": "infra",
    }

    def __init__(self, pull_fn: callable | None = None) -> None:
        self._pull = pull_fn or vb.parquet_pull

    def load(
        self,
        symbols: Iterable[str],
        start: str | None = None,
        end: str | None = None,
        columns: Sequence[str] = ("open", "high", "low", "close", "volume"),
        timeframe: str | None = None,
        tz: str = "UTC",
    ) -> OhlcvFrameDTO:
        log = build_logger()
        with time_phase(
            log,
            "parquet_pull",
            symbol=",".join(list(symbols)),
            timeframe=str(timeframe or ""),
            session="",
        ):
            df = self._pull(symbols, start, end, columns, timeframe, tz)
        if not isinstance(df.index, pd.DatetimeIndex) or df.index.tz is None:
            raise ValueError("Data index must be timezone-aware")
        # 列名は小文字に正規化
        df.columns = [str(c).lower() for c in df.columns]
        # Open必須（次足Open約定のため）
        if "open" not in df.columns:
            raise ValueError("open column is required")
        return OhlcvFrameDTO(frame=df, freq=None)
