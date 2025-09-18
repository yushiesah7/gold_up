from __future__ import annotations

import contextlib
from collections.abc import Mapping
from typing import Any, ClassVar

import pandas as pd

from trade_app.adapters.vbtpro import vbtpro_bindings as vb
from trade_app.domain.dto.ohlcv_frame import OhlcvFrameDTO
from trade_app.domain.ports.backtest import BacktestPort


class VbtProBacktestAdapter(BacktestPort):
    """vbt( PRO ) へ from_signals / CV を委譲する実装。"""

    __responsibility__: ClassVar[str] = "vbt( PRO ) 実行へのアダプタ"
    __debt_reason__: ClassVar[dict[str, str]] = {
        "reason": "vbt PRO の API 差異は bindings 内で吸収",
        "owner": "infra",
    }

    def __init__(
        self,
        from_signals_fn: Any | None = None,
        ohlc_builder_fn: Any | None = None,
    ) -> None:
        # DI 可：ユニットテストではここをモックできる
        self._from_signals = from_signals_fn or vb.portfolio_from_signals
        self._make_ohlc = ohlc_builder_fn or vb.make_ohlc_data

    def run_from_signals(
        self,
        ohlcv: OhlcvFrameDTO,
        entries: pd.Series,
        exits: pd.Series,
        params: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        df = ohlcv.frame
        if "open" not in df.columns:
            raise ValueError("open column is required for NextOpen execution")
        # 契約: NextOpen 約定。bindings 内で price='open' 等に解決させるため OHLC を渡す
        ohlc_like = self._make_ohlc(df[["open", "high", "low", "close"]])

        pf = self._from_signals(
            ohlc_like,
            entries=entries.astype(bool),
            exits=exits.astype(bool),
            params=params or {},
        )
        # 返却形式は最小のサマリ＋生オブジェクト（呼び手で自由に拡張）
        result: dict[str, Any] = {
            "portfolio": pf,
            "index": df.index,
        }
        # スタッツが取れる環境なら拾って返す（bindingsの薄ラッパを使用）
        # 例外が出ても無視して処理を続ける
        with contextlib.suppress(Exception):
            result.update(vb.portfolio_metrics(pf))
        return result

    def run_cv(
        self,
        ohlcv: OhlcvFrameDTO,
        entries: pd.Series,
        exits: pd.Series,
        splits: list[tuple[pd.Index, pd.Index]],
        params: Mapping[str, Any] | None = None,
    ) -> list[Mapping[str, Any]]:
        """Purged / Embargoed などで作った split をそのまま流し込む"""
        out: list[Mapping[str, Any]] = []
        for _train_idx, test_idx in splits:
            # 一般的には test 区間に対して実行し、train は探索・学習用途
            e_test = entries.loc[test_idx]
            x_test = exits.loc[test_idx]
            o_test = OhlcvFrameDTO(frame=ohlcv.frame.loc[test_idx], freq=ohlcv.freq)
            out.append(self.run_from_signals(o_test, e_test, x_test, params))
        return out
