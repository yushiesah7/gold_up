from __future__ import annotations

import pandas as pd


def donchian(high: pd.Series, low: pd.Series, window: int = 20) -> dict[str, pd.Series]:
    """Donchian Channel（upper/middle/lower）"""
    upper = high.rolling(window, min_periods=window).max()
    lower = low.rolling(window, min_periods=window).min()
    middle = (upper + lower) / 2.0
    upper.name = "upper"
    middle.name = "middle"
    lower.name = "lower"
    return {"upper": upper, "middle": middle, "lower": lower}
