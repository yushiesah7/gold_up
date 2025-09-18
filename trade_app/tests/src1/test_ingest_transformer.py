import pandas as pd
import pytz

from trade_app.domain.services.ingest_transformer import normalize_ohlcv


def test_normalize_ohlcv_basic_utc_index_and_columns():
    # MT5風の生データ
    idx = pd.date_range("2024-01-01", periods=3, freq="h", tz=pytz.UTC)
    raw = pd.DataFrame(
        {
            "time": idx.tz_convert(None).view("int64") // 10**9,
            "open": [1, 2, 3],
            "high": [2, 3, 4],
            "low": [0, 1, 2],
            "close": [1, 2, 3],
            "tick_volume": [10, 11, 12],
        }
    )
    df = normalize_ohlcv(raw, origin_tz="UTC", target_tz="UTC")
    assert df.index.tz is not None
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert df.loc[idx[0], "open"] == 1
