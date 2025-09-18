from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class ScorerPort(Protocol):
    """メトリクスdict を単一スコアへ射影（最大化）"""

    __responsibility__ = "SharpeやReturnを統合してスカラーにする"

    def score(self, metrics_summary: Mapping[str, Any]) -> float: ...
