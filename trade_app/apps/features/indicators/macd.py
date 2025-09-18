from __future__ import annotations

import pandas as pd


def macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict[str, pd.Series]:
    """MACD（macd/signal/hist）"""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    macd_line.name = "macd"
    signal_line.name = "signal"
    hist.name = "hist"
    return {"macd": macd_line, "signal": signal_line, "hist": hist}
