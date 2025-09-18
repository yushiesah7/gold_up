from __future__ import annotations

import pandas as pd


def vwap(
    price: pd.Series,
    volume: pd.Series,
    window: int | None = None,
) -> pd.Series:
    """VWAP（window=Noneなら累積、それ以外はローリング）"""
    pv = price * volume
    vol = volume.replace(0, pd.NA)

    if window is None:
        out = pv.cumsum() / vol.cumsum()
        out.name = "vwap"
        return out

    out = (
        pv.rolling(window, min_periods=window).sum() / vol.rolling(window, min_periods=window).sum()
    )
    out.name = f"vwap_{window}"
    return out
