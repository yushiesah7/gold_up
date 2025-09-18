from types import SimpleNamespace

import pandas as pd
import pytz

from trade_app.adapters.vbtpro.backtest_adapter import VbtProBacktestAdapter
from trade_app.domain.dto.ohlcv_frame import OhlcvFrameDTO


def test_backtest_adapter_from_signals_with_di():
    # データ作成
    idx = pd.date_range("2024-01-01", periods=10, freq="h", tz=pytz.UTC)
    df = pd.DataFrame(
        {
            "open": pd.Series(range(10), index=idx, dtype=float),
            "high": pd.Series(range(1, 11), index=idx, dtype=float),
            "low": pd.Series(range(10), index=idx, dtype=float) - 1,
            "close": pd.Series(range(10), index=idx, dtype=float),
            "volume": pd.Series(1, index=idx, dtype=float),
        },
        index=idx,
    )
    dto = OhlcvFrameDTO(frame=df, freq="h")

    # エントリ/イグジット（単純：前半でin → 後半でout）
    entries = pd.Series([True] * 5 + [False] * 5, index=idx)
    exits = pd.Series([False] * 5 + [True] * 5, index=idx)

    # DI: vbt PRO 呼び出しを偽装
    def fake_make_ohlc(d):
        # OHLCData の代わりに DataFrame を通しても良い（Adapter 内で透過）
        assert {"open", "high", "low", "close"}.issubset(d.columns)
        return d

    def fake_from_signals(price_like, entries, exits, *, params):
        # 価格は open を使う契約（NextOpen 約定は signals 側で pre_shift=1 済み）
        assert "open" in price_like.columns
        # 擬似的な戻り値（実オブジェクトに似た形）
        return SimpleNamespace(total_return=0.1234, stats={"trades": 1})

    adapter = VbtProBacktestAdapter(
        from_signals_fn=fake_from_signals,
        ohlc_builder_fn=fake_make_ohlc,
    )
    result = adapter.run_from_signals(dto, entries, exits, params={"fees": 0.001})
    assert "portfolio" in result
    assert result.get("total_return", 0.0) == 0.1234
    assert result.get("stats", {}).get("trades") == 1
