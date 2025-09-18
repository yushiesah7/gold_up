import pandas as pd
import pytz

from trade_app.apps.features.indicators.rsi import rsi


def test_rsi_basic_monotonic_up():
    idx = pd.date_range("2024-01-01", periods=20, freq="h", tz=pytz.UTC)
    close = pd.Series(range(20), index=idx, name="close").astype(float)
    out = rsi(close, length=14)
    assert out.index.equals(close.index)
    assert out.iloc[-1] > 50
