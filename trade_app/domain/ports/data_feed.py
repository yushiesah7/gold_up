from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from trade_app.domain.dto.ohlcv_frame import OhlcvFrameDTO


class DataFeedPort(Protocol):
    """OHLCVデータを期間・列指定で取得する抽象I/F（UTC aware index を契約）"""

    __responsibility__ = "履歴データ取得の抽象境界（I/OはAdapter側）"

    def load(
        self,
        symbols: Iterable[str],
        start: str | None = None,
        end: str | None = None,
        columns: tuple[str, ...] = ("open", "high", "low", "close", "volume"),
        timeframe: str | None = None,
        tz: str = "UTC",
    ) -> OhlcvFrameDTO: ...
