from __future__ import annotations

import pandas as pd


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(length, min_periods=length).mean()


essential_upper = {"upper", "middle", "lower"}


def keltner(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    ema_len: int = 20,
    atr_len: int = 14,
    mult: float = 2.0,
) -> dict[str, pd.Series]:
    """Keltner Channel（upper/middle/lower）"""
    mid = close.ewm(span=ema_len, adjust=False).mean()
    atr = _atr(high, low, close, atr_len)
    upper = mid + mult * atr
    lower = mid - mult * atr
    upper.name = "upper"
    mid.name = "middle"
    lower.name = "lower"
    return {"upper": upper, "middle": mid, "lower": lower}
