from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pandas as pd


class ParquetSinkPort(Protocol):
    """Parquet書き出しの抽象。ファイルシステム/雲は実装側。"""

    __responsibility__ = "正規化済みOHLCVをParquetに保存"

    def write(
        self,
        df: pd.DataFrame,  # index=UTC aware DatetimeIndex, cols=open...volume
        base_dir: Path,
        symbol: str,
        timeframe: str,
        *,
        filename: str | None = None,  # 省略時 "symbol_timeframe.parquet"
        engine: str = "pyarrow",
        compression: str = "snappy",
    ) -> Path: ...
