from __future__ import annotations

import pandas as pd


def stoch(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k: int = 14,
    d: int = 3,
    smooth: int = 1,
) -> dict[str, pd.Series]:
    """Stochastic %K/%D（fast Kをsmooth、Dは移動平均）"""
    lowest = low.rolling(k, min_periods=k).min()
    highest = high.rolling(k, min_periods=k).max()
    denom = (highest - lowest).replace(0, pd.NA)
    k_fast = (close - lowest) / denom * 100.0
    if smooth and smooth > 1:
        k_fast = k_fast.rolling(smooth, min_periods=smooth).mean()
    d_line = k_fast.rolling(d, min_periods=d).mean()
    k_fast.name = "k"
    d_line.name = "d"
    return {"k": k_fast, "d": d_line}
