from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

import pandas as pd


class ResultsSinkPort(Protocol):
    """研究結果（fold表＋サマリ）の永続化I/F。出力形式や保存先は実装側で吸収。"""

    __responsibility__ = "WFA等の検証結果をファイルへ保存する抽象境界"

    def write(
        self,
        table: pd.DataFrame,
        summary: Mapping[str, Any],
        base_dir: Path,
        experiment_name: str,
        *,
        fmt: str = "parquet",
        with_timestamp_dir: bool = True,
    ) -> Mapping[str, Path]: ...
