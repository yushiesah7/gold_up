from pathlib import Path

import pandas as pd
import pytest
import pytz

from trade_app.adapters.parquet.parquet_sink_adapter import ParquetSinkAdapter

pytest.importorskip("pyarrow")  # pyarrowがなければskip


def test_parquet_sink_writes_and_reads(tmp_path: Path):
    idx = pd.date_range("2024-01-01", periods=3, freq="h", tz=pytz.UTC)
    df = pd.DataFrame(
        {
            "open": [1, 2, 3],
            "high": [2, 3, 4],
            "low": [0, 1, 2],
            "close": [1, 2, 3],
            "volume": [10, 11, 12],
        },
        index=idx,
    )
    sink = ParquetSinkAdapter()
    path = sink.write(df, tmp_path, "EURUSD", "h1")
    assert path.exists()
    back = pd.read_parquet(path)
    assert back.index.tz is not None
    assert "open" in back.columns
