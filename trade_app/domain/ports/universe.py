from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class UniversePort(Protocol):
    """利用可能なシンボル/時間足/セッションの列挙（実装差替え可: defaults/MT5/DB等）"""

    __responsibility__ = "自動探索の外側ループ対象を列挙する"

    def list_symbols(self) -> Sequence[str]: ...

    def list_timeframes(self) -> Sequence[str]: ...

    def list_sessions(self) -> Sequence[str]: ...
