from __future__ import annotations

import pandas as pd


def roc(series: pd.Series, window: int = 12, scale: float = 100.0) -> pd.Series:
    """Rate of Change（%）"""
    out = (series / series.shift(window) - 1.0) * scale
    out.name = f"roc_{window}"
    return out
