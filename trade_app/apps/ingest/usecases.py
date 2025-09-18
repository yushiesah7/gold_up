from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from trade_app.domain.dto.ingest_result import IngestResultDTO
from trade_app.domain.ports.history_source import HistorySourcePort
from trade_app.domain.ports.parquet_sink import ParquetSinkPort
from trade_app.domain.services.ingest_transformer import DEFAULT_MAP, normalize_ohlcv


def ingest_history_to_parquet(
    *,
    source: HistorySourcePort,
    sink: ParquetSinkPort,
    symbols: Iterable[str],
    timeframe: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    base_dir: Path,
    colmap: Mapping[str, str] | None = None,
    origin_tz: str | None = "UTC",
    target_tz: str = "UTC",
    sink_kwargs: Mapping[str, Any] | None = None,
) -> list[IngestResultDTO]:
    """各シンボルについて fetch→normalize→write を実行。結果サマリを返す。"""
    results: list[IngestResultDTO] = []
    for sym in symbols:
        raw = source.fetch_ohlcv(sym, timeframe, start, end)
        # colmap未指定ならデフォルトマップを使う（空dictで上書きしない）
        norm = normalize_ohlcv(
            raw,
            colmap=colmap or DEFAULT_MAP,
            origin_tz=origin_tz,
            target_tz=target_tz,
        )
        path = sink.write(
            norm,
            base_dir=base_dir,
            symbol=sym,
            timeframe=timeframe,
            **(sink_kwargs or {}),
        )
        results.append(IngestResultDTO(symbol=sym, timeframe=timeframe, rows=len(norm), path=path))
    return results
