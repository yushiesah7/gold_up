import pandas as pd
import pytz

from trade_app.apps.features.pipeline.feature_bundler import bundle_features
from trade_app.domain.dto.ohlcv_frame import OhlcvFrameDTO


def test_bundler_drops_head_nans():
    idx = pd.date_range("2024-01-01", periods=10, freq="min", tz=pytz.UTC)
    df = pd.DataFrame({"open": 1, "high": 1, "low": 1, "close": 1}, index=idx)
    ohlcv = OhlcvFrameDTO(frame=df)
    s = pd.Series([None, None, 1, 2, 3, 4, 5, 6, 7, 8], index=idx, name="feat")
    fb = bundle_features(ohlcv, {"feat": s}, nan_policy="drop_head")
    assert fb.features.index[0] == idx[2]
    assert not fb.features.isna().any().any()
