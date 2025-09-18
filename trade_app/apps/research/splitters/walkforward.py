from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from trade_app.domain.ports.split_strategy import SplitStrategyPort


class WalkForwardSplitter(SplitStrategyPort):
    """ロール型WFA: train_size bars の直後に test_size bars をOOSとしてロール"""

    def __init__(self, train_size: int, test_size: int, step: int | None = None) -> None:
        if train_size <= 0 or test_size <= 0:
            raise ValueError("train_size/test_size は正の整数が必要")
        self.train_size = int(train_size)
        self.test_size = int(test_size)
        self.step = int(step) if step is not None else int(test_size)

    def split(self, index: pd.DatetimeIndex) -> Sequence[tuple[pd.Timestamp, pd.Timestamp]]:
        n = len(index)
        if n < self.train_size + self.test_size:
            return []
        out: list[tuple[pd.Timestamp, pd.Timestamp]] = []
        start_pos = self.train_size
        while start_pos + self.test_size <= n:
            oos_start = index[start_pos]
            oos_end = index[start_pos + self.test_size - 1]
            out.append((oos_start, oos_end))
            start_pos += self.step
        return out
