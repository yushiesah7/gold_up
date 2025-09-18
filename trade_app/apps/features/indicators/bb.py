from __future__ import annotations

import pandas as pd


def bb(
    close: pd.Series,
    window: int = 20,
    mult: float = 2.0,
    use_ema: bool = False,
) -> dict[str, pd.Series]:
    """Bollinger Bands（upper/middle/lower）。先頭はNaNが出る。"""
    if use_ema:
        mid = close.ewm(span=window, adjust=False).mean()
        # EWMに厳密な“標準偏差”を合わせる簡易実装（近似）
        std = (close - mid).abs().ewm(span=window, adjust=False).mean()
    else:
        mid = close.rolling(window, min_periods=window).mean()
        std = close.rolling(window, min_periods=window).std(ddof=0)
    upper = mid + mult * std
    lower = mid - mult * std
    upper.name = "upper"
    mid.name = "middle"
    lower.name = "lower"
    return {"upper": upper, "middle": mid, "lower": lower}
