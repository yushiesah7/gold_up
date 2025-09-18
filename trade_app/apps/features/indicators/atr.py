from __future__ import annotations

import pandas as pd


def atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = (high - low).abs()
    tr = pd.concat([tr, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    out = tr.rolling(length, min_periods=length).mean()
    out.name = f"atr_{length}"
    return out
