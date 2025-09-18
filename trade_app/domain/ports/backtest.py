from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

import pandas as pd

from trade_app.domain.dto.ohlcv_frame import OhlcvFrameDTO


class BacktestPort(Protocol):
    """検証実行の抽象Port。vbt PRO 直結は Adapter 側に隔離。"""

    __responsibility__ = "from_signals/WFA/CV を統一契約で実行"

    def run_from_signals(
        self,
        ohlcv: OhlcvFrameDTO,
        entries: pd.Series,  # bool 同Index
        exits: pd.Series,  # bool 同Index
        params: Mapping[str, Any] | None = None,  # 手数料/スリッページ/サイズ/ストップ等
    ) -> Mapping[str, Any]: ...

    def run_cv(
        self,
        ohlcv: OhlcvFrameDTO,
        entries: pd.Series,
        exits: pd.Series,
        splits: list[tuple[pd.Index, pd.Index]],  # [(train_idx, test_idx), ...]
        params: Mapping[str, Any] | None = None,
    ) -> list[Mapping[str, Any]]: ...
