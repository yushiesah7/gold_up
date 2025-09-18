from types import SimpleNamespace

import pandas as pd
import pytz

from trade_app.adapters.vbtpro.backtest_adapter import VbtProBacktestAdapter
from trade_app.domain.dto.ohlcv_frame import OhlcvFrameDTO


def test_vbtpro_adapter_calls_bindings(monkeypatch):
    calls: dict[str, object] = {}

    def fake_make_ohlc(df: pd.DataFrame):  # passthrough for assertion
        calls["ohlc_cols"] = list(df.columns)
        return df

    def fake_from_signals(price_like, entries, exits, params):
        calls["price_cols"] = list(getattr(price_like, "columns", []))
        calls["entries_true"] = bool(pd.Series(entries).any())
        calls["exits_true"] = bool(pd.Series(exits).any())
        calls["params"] = dict(params)
        return SimpleNamespace()  # portfolio stub

    def fake_metrics(portfolio):
        return {"total_return": 0.0}

    import trade_app.adapters.vbtpro.vbtpro_bindings as vb  # noqa: PLC0415

    monkeypatch.setattr(vb, "make_ohlc_data", fake_make_ohlc, raising=True)
    monkeypatch.setattr(vb, "portfolio_from_signals", fake_from_signals, raising=True)
    monkeypatch.setattr(vb, "portfolio_metrics", fake_metrics, raising=True)

    # reload adapter module is not necessary because adapter looks up bindings in __init__
    idx = pd.date_range("2024-01-01", periods=5, freq="h", tz=pytz.UTC)
    df = pd.DataFrame(
        {
            "open": pd.Series([1, 2, 3, 4, 5], index=idx, dtype=float),
            "high": pd.Series([2, 3, 4, 5, 6], index=idx, dtype=float),
            "low": pd.Series([0, 1, 2, 3, 4], index=idx, dtype=float),
            "close": pd.Series([1, 2, 3, 4, 5], index=idx, dtype=float),
            "volume": pd.Series([1, 1, 1, 1, 1], index=idx, dtype=float),
        },
        index=idx,
    )
    ohlcv = OhlcvFrameDTO(frame=df, freq="h")
    entries = pd.Series([False, True, False, False, False], index=idx)
    exits = pd.Series([False, False, True, False, False], index=idx)

    adapter = VbtProBacktestAdapter()
    out = adapter.run_from_signals(ohlcv, entries, exits, params={"fees": 0.001})

    assert "portfolio" in out
    assert "index" in out and out["index"].equals(df.index)
    assert calls["ohlc_cols"] == ["open", "high", "low", "close"]
    assert calls["price_cols"] == ["open", "high", "low", "close"]
    assert calls["entries_true"] is True and calls["exits_true"] is True
    assert calls["params"]["fees"] == 0.001
