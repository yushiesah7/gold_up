import pandas as pd
import pytz

from trade_app.domain.dto.ohlcv_frame import OhlcvFrameDTO


def test_ohlcv_dto_requires_utc_aware_index():
    idx = pd.date_range("2024-01-01", periods=3, freq="D", tz=pytz.UTC)
    df = pd.DataFrame(
        {"open": [1, 2, 3], "high": [2, 3, 4], "low": [0, 1, 2], "close": [1.5, 2.5, 3.5]},
        index=idx,
    )
    dto = OhlcvFrameDTO(frame=df, freq="D")
    assert dto.frame.index.tz is not None
