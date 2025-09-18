import pandas as pd
import pytz

from trade_app.adapters.vbtpro.data_feed_adapter import VbtProDataFeedAdapter


def test_data_feed_adapter_calls_pull(monkeypatch):
    idx = pd.date_range("2024-01-01", periods=3, freq="h", tz=pytz.UTC)
    df = pd.DataFrame(
        {"open": [1, 2, 3], "high": [2, 3, 4], "low": [0, 1, 2], "close": [1, 2, 3]}, index=idx
    )

    def fake_pull(symbols, start, end, columns, timeframe, tz):
        assert list(symbols) == ["EURUSD"]
        assert tz == "UTC"
        return df

    adapter = VbtProDataFeedAdapter(pull_fn=fake_pull)
    dto = adapter.load(["EURUSD"])
    assert dto.frame.equals(df)
