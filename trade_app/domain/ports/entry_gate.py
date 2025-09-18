from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

import pandas as pd


class EntryGatePort(Protocol):
    """entries/exits と features を受け取り、制約（セッション/DST/同時保有数）で entries をゲート"""

    __responsibility__ = "セッション/DST/ポジション制約を信号に適用"

    def gate(
        self,
        *,
        entries: pd.Series,
        exits: pd.Series,
        features: pd.DataFrame,
        context: Mapping[str, Any] | None = None,
    ) -> pd.Series: ...
