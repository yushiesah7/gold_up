from __future__ import annotations

import pandas as pd


def sma(series: pd.Series, length: int = 20) -> pd.Series:
    out = series.rolling(length, min_periods=length).mean()
    out.name = f"sma_{length}"
    return out


def ema(series: pd.Series, length: int = 20) -> pd.Series:
    out = series.ewm(span=length, adjust=False).mean()
    out.name = f"ema_{length}"
    return out
