from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import ClassVar

from trade_app.domain.dto.ohlcv_frame import OhlcvFrameDTO
from trade_app.domain.ports.data_feed import DataFeedPort

__responsibility__: ClassVar[str] = "DataFeedPortを呼んでOHLCV DTOを得る（I/O禁止・整形はPort側）"


def load_ohlcv(
    feed: DataFeedPort,
    symbols: Iterable[str],
    *,
    start: str | None = None,
    end: str | None = None,
    columns: Sequence[str] = ("open", "high", "low", "close", "volume"),
    timeframe: str | None = None,
    tz: str = "UTC",
) -> OhlcvFrameDTO:
    """外部依存はPortに隔離。ここは契約どおりDTOを受け取るだけ。"""
    return feed.load(
        symbols=symbols,
        start=start,
        end=end,
        columns=tuple(columns),
        timeframe=timeframe,
        tz=tz,
    )
