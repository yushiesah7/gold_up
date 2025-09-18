from __future__ import annotations

from collections.abc import Sequence

from trade_app.config.defaults import DEFAULT_SYMBOLS, DEFAULT_TIMEFRAMES, SESSIONS_PRESETS
from trade_app.domain.ports.universe import UniversePort


class DefaultUniverseAdapter(UniversePort):
    """config.defaults をユニバースとして返す最小実装"""

    def list_symbols(self) -> Sequence[str]:
        return list(DEFAULT_SYMBOLS)

    def list_timeframes(self) -> Sequence[str]:
        return list(DEFAULT_TIMEFRAMES)

    def list_sessions(self) -> Sequence[str]:
        return list(SESSIONS_PRESETS.keys())
