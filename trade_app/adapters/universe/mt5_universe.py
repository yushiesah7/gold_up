from __future__ import annotations

from collections.abc import Sequence

# オプショナル依存（未導入なら None）。PLC0415 回避のためトップレベルで処理。
try:  # pragma: no cover - import guard
    import MetaTrader5 as mt5  # type: ignore
except Exception:  # pragma: no cover - optional dep
    mt5 = None  # type: ignore

from trade_app.adapters.universe.default_universe import DefaultUniverseAdapter
from trade_app.config.defaults import DEFAULT_TIMEFRAMES
from trade_app.domain.ports.universe import UniversePort


class MT5UniverseAdapter(UniversePort):
    """
    MT5 ターミナルからシンボルを列挙する Universe 実装。

    - symbols: MetaTrader5.symbols_get() を使用
    - timeframes: APIに“利用可能TF列挙”は無いため当面は defaults を返す
    - sessions: presets 依存のため DefaultUniverseAdapter に委譲する運用を推奨

    MetaTrader5 が未インストール/未初期化の環境では空リストを返します。
    """

    def __init__(self, pattern: str = "*") -> None:
        self.pattern = pattern

    def list_symbols(self) -> Sequence[str]:
        # 未導入/初期化不可時は空配列でフォールバック
        if mt5 is None:
            return []
        try:  # pragma: no cover - 実機依存
            # 初期化（すでに init 済みの場合は True が返る）
            mt5.initialize()
        except Exception:
            return []
        syms = mt5.symbols_get(self.pattern)
        if not syms:
            return []
        return [s.name for s in syms]

    def list_timeframes(self) -> Sequence[str]:
        return list(DEFAULT_TIMEFRAMES)

    def list_sessions(self) -> Sequence[str]:
        # セッションは presets 依存（config.defaults）
        return DefaultUniverseAdapter().list_sessions()
