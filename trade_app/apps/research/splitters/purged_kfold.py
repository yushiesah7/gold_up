from __future__ import annotations

import math
from collections.abc import Sequence

import pandas as pd

from trade_app.domain.ports.split_strategy import SplitStrategyPort


class PurgedKFoldSplitter(SplitStrategyPort):
    """
    時系列を K 分割し、各foldをOOSとして返す（trainは“その周囲 embargo”でパージ）。
    - 返却は OOS (start,end) のみ（trainの構成は上位で推定/利用）。
    - embargo は“前後に何bar空けるか”を bar 単位で指定。
    """

    def __init__(self, n_splits: int, embargo: int = 0) -> None:
        if n_splits < 2:  # noqa: PLR2004
            raise ValueError("n_splits must be >= 2")
        if embargo < 0:
            raise ValueError("embargo must be >= 0")
        self.n_splits = int(n_splits)
        self.embargo = int(embargo)

    def split(self, index: pd.DatetimeIndex) -> Sequence[tuple[pd.Timestamp, pd.Timestamp]]:
        n = len(index)
        if n < self.n_splits:
            return []
        fold_size = math.floor(n / self.n_splits)
        out: list[tuple[pd.Timestamp, pd.Timestamp]] = []
        for k in range(self.n_splits):
            start_i = k * fold_size
            end_i = (k + 1) * fold_size - 1 if k < self.n_splits - 1 else n - 1
            # embargo 自体は train 構成時に使うが、OOS 定義には影響を与えない
            oos_start = index[start_i]
            oos_end = index[end_i]
            out.append((oos_start, oos_end))
        return out
