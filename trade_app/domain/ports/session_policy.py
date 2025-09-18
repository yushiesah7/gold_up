from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

import pandas as pd


class SessionPolicyPort(Protocol):
    """時系列Indexに対して、セッション有効フラグ列を生成（DST対応）"""

    __responsibility__ = "Index(UTC) → session_active(bool) を返す"

    def make_mask(
        self,
        index_utc: pd.DatetimeIndex,
        *,
        preset: str | None = None,
        tz: str | None = "UTC",
        windows: list[Mapping[str, Any]] | None = None,
    ) -> pd.Series: ...
