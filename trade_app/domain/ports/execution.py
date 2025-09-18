from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar, Protocol


class MT5ConnectionPort(Protocol):
    """MT5接続系の抽象Port（構造的型）。外部API差し替え点。"""

    __responsibility__: ClassVar[str] = "MT5接続・情報取得の抽象I/F"
    __debt_reason__: ClassVar[dict[str, str]] = {
        "reason": "デモ/本番・ベンダ差し替えを容易にするためProtocol採用",
        "owner": "architecture",
        "until": "2026-01-01",
    }

    def connect(self, account: int, password: str, server: str) -> bool: ...
    def disconnect(self) -> None: ...
    def is_connected(self) -> bool: ...
    def get_account_info(self) -> Mapping[str, Any] | None: ...
    def get_symbol_info(self, symbol: str) -> Mapping[str, Any] | None: ...
