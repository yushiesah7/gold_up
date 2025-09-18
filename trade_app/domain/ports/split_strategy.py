from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

import pandas as pd


class SplitStrategyPort(Protocol):
    """検証用の時系列分割（WFA / Purged CV など）の抽象I/F"""

    __responsibility__ = "Indexに対して学習/検証期間の分割を返す"

    def split(self, index: pd.DatetimeIndex) -> Sequence[tuple[pd.Timestamp, pd.Timestamp]]:
        """index 全体に対し、検証ターゲット期間（OOS）を表す (start,end] の連を返す"""
        ...
