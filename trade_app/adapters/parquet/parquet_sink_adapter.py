from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pandas as pd

from trade_app.domain.ports.parquet_sink import ParquetSinkPort


class ParquetSinkAdapter(ParquetSinkPort):
    """pandas.to_parquetで保存（pyarrow推奨）。Path返却。"""

    __responsibility__: ClassVar[str] = "Parquet書き出しの実装（ローカルFS想定）"
    __debt_reason__: ClassVar[dict[str, str]] = {
        "reason": "クラウド/パーティション分割は将来対応（ここで吸収）",
        "owner": "infra",
    }

    def write(
        self,
        df: pd.DataFrame,
        base_dir: Path,
        symbol: str,
        timeframe: str,
        *,
        filename: str | None = None,
        engine: str = "pyarrow",
        compression: str = "snappy",
    ) -> Path:
        base_dir.mkdir(parents=True, exist_ok=True)
        fname = filename or f"{symbol}_{timeframe}.parquet"
        path = base_dir / fname
        df.to_parquet(path, engine=engine, compression=compression, index=True)
        return path
