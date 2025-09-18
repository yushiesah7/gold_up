from pathlib import Path

import pandas as pd
import pytest
import pytz

from trade_app.adapters.parquet.parquet_sink_adapter import ParquetSinkAdapter
from trade_app.apps.ingest.usecases import ingest_history_to_parquet
from trade_app.domain.ports.history_source import HistorySourcePort

pytest.importorskip("pyarrow")  # 実書きテストはpyarrow前提


class FakeSource(HistorySourcePort):
    def fetch_ohlcv(self, symbol, timeframe, start, end):
        idx = pd.date_range(start, periods=5, freq="h", tz=pytz.UTC)
        raw = pd.DataFrame(
            {
                "time": idx.tz_convert(None).view("int64") // 10**9,
                "open": [1, 2, 3, 4, 5],
                "high": [2, 3, 4, 5, 6],
                "low": [0, 1, 2, 3, 4],
                "close": [1, 2, 3, 4, 5],
                "tick_volume": [10, 11, 12, 13, 14],
            }
        )
        return raw


def test_ingest_usecase_e2e(tmp_path: Path):
    res = ingest_history_to_parquet(
        source=FakeSource(),
        sink=ParquetSinkAdapter(),
        symbols=["EURUSD", "USDJPY"],
        timeframe="h1",
        start=pd.Timestamp("2024-01-01 00:00", tz=pytz.UTC),
        end=pd.Timestamp("2024-01-01 04:00", tz=pytz.UTC),
        base_dir=tmp_path,
        origin_tz="UTC",
        target_tz="UTC",
    )
    assert len(res) == 2
    for r in res:
        assert r.rows == 5
        assert r.path.exists()
