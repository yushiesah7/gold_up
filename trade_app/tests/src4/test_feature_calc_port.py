import pandas as pd
import pytz

from trade_app.apps.features.feature_calc import DefaultFeatureCalculator
from trade_app.domain.dto.ohlcv_frame import OhlcvFrameDTO


def test_feature_calc_port_basic():
    idx = pd.date_range("2024-01-01", periods=60, freq="h", tz=pytz.UTC)
    df = pd.DataFrame(
        {
            "open": pd.Series(range(60), index=idx, dtype=float),
            "high": pd.Series(range(1, 61), index=idx, dtype=float),
            "low": pd.Series(range(60), index=idx, dtype=float) - 1,
            "close": pd.Series(range(60), index=idx, dtype=float),
            "volume": pd.Series(1, index=idx, dtype=float),
        },
        index=idx,
    )
    dto = OhlcvFrameDTO(frame=df, freq="h")

    calc = DefaultFeatureCalculator()
    spec = {
        "rsi_14": {"kind": "rsi", "on": "close", "params": {"length": 14}},
        "sma_20": {"kind": "sma", "on": "close", "params": {"length": 20}},
        "atr_14": {
            "kind": "atr",
            "on": ["high", "low", "close"],
            "params": {"length": 14},
        },
    }
    bundle = calc.compute(dto, spec)
    assert set(bundle.features.columns) == {"rsi_14", "sma_20", "atr_14"}
    assert not bundle.features.isna().any().any()
    # drop_head により最初の有効行は少なくとも 20 本目以降
    assert bundle.features.index[0] >= idx[19]
