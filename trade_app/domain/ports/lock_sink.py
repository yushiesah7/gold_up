from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol


class LockSinkPort(Protocol):
    """最良結果を lock ファイルに保存"""

    __responsibility__ = "spec.lock.json 等の出力"

    def write(
        self,
        *,
        best_params: Mapping[str, Any],
        best_score: float,
        features_spec: Mapping[str, Any],
        plan_spec: Mapping[str, Any],
        space: Mapping[str, Any],
        out_dir: Path,
        filename: str = "spec.lock.json",
    ) -> Path: ...
