from __future__ import annotations

import pandas as pd


def zscore(series: pd.Series, window: int = 20) -> pd.Series:
    """ローリングZスコア"""
    mean = series.rolling(window, min_periods=window).mean()
    std = series.rolling(window, min_periods=window).std(ddof=0)
    out = (series - mean) / std
    out.name = f"z_{window}"
    return out
