from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from trade_app.domain.dto.feature_bundle import FeatureBundleDTO
from trade_app.domain.dto.ohlcv_frame import OhlcvFrameDTO


class FeatureCalcPort(Protocol):
    """決定的な指標計算（同Index/同長保証、外部I/O禁止）"""

    __responsibility__ = "features作成（決定的計算のみ）"

    def compute(
        self,
        ohlcv: OhlcvFrameDTO,
        spec: Mapping[str, Mapping[str, Any]],
    ) -> FeatureBundleDTO: ...
