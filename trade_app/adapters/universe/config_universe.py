from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, ClassVar

from trade_app.domain.ports.universe import UniversePort


class ConfigUniverseAdapter(UniversePort):
    """
    シンプルなUniverse:
      - コンストラクタに dict を渡すか、未指定なら既定（主要FX）を返す
      - 例: {"symbols": ["EURUSD","USDJPY"], "timeframes": ["m15","h1"]}
    """

    __responsibility__: ClassVar[str] = "研究用の固定ユニバース定義（将来MT5/DB差替え）"

    def __init__(self, cfg: Mapping[str, Any] | None = None) -> None:
        self._symbols = list((cfg or {}).get("symbols", ["EURUSD", "USDJPY"]))
        self._tfs = list((cfg or {}).get("timeframes", ["m15", "h1", "h4"]))

    def list_symbols(self) -> Sequence[str]:
        return self._symbols

    def list_timeframes(self) -> Sequence[str]:
        return self._tfs
