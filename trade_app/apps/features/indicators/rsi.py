from __future__ import annotations

import pandas as pd


def rsi(close: pd.Series, length: int = 14) -> pd.Series:
    """標準RSI（NaNは先頭にのみ生成）"""
    delta = close.diff()
    up = delta.clip(lower=0)
    down = (-delta).clip(lower=0)
    roll_up = up.ewm(alpha=1 / length, adjust=False).mean()
    roll_down = down.ewm(alpha=1 / length, adjust=False).mean()
    rs = roll_up / roll_down
    out = 100 - (100 / (1 + rs))
    out.name = f"rsi_{length}"
    return out
