from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol


class SpecLoaderPort(Protocol):
    """features/plan を外部ファイル（YAML等）から取得する抽象"""

    __responsibility__ = "仕様ロードの抽象I/F"

    def load(self, path: Path) -> tuple[Mapping[str, Mapping], Mapping]:
        """
        Returns:
          features_spec: Mapping[str, Mapping]
          plan_spec: Mapping
        """
        ...
