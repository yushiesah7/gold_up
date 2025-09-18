import pandas as pd
import pytz

from trade_app.apps.features.pipeline.loader import load_ohlcv
from trade_app.domain.dto.ohlcv_frame import OhlcvFrameDTO
from trade_app.domain.ports.data_feed import DataFeedPort


class FakeFeed(DataFeedPort):
    def load(
        self,
        symbols,
        start=None,
        end=None,
        columns=("open", "high", "low", "close", "volume"),
        timeframe=None,
        tz="UTC",
    ) -> OhlcvFrameDTO:
        idx = pd.date_range("2024-01-01", periods=3, freq="h", tz=pytz.UTC)
        df = pd.DataFrame(
            {
                "open": [1, 2, 3],
                "high": [2, 3, 4],
                "low": [0, 1, 2],
                "close": [1, 2, 3],
                "volume": [1, 1, 1],
            },
            index=idx,
        )
        return OhlcvFrameDTO(frame=df, freq="h")


def test_loader_returns_dto():
    dto = load_ohlcv(FakeFeed(), ["EURUSD"])
    assert isinstance(dto, OhlcvFrameDTO)
    assert {"open", "high", "low", "close"}.issubset(dto.frame.columns)
