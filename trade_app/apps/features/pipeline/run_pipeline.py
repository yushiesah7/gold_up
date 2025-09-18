from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, ClassVar

from trade_app.apps.features.pipeline.loader import load_ohlcv
from trade_app.domain.dto.pipeline_output import PipelineOutputDTO
from trade_app.domain.ports.data_feed import DataFeedPort
from trade_app.domain.ports.feature_calc import FeatureCalcPort
from trade_app.domain.ports.plan_builder import PlanBuilderPort

__responsibility__: ClassVar[str] = "src4の統合（OHLCV→features→plan）。純関数呼び出しはしない。"


def run_pipeline(
    *,
    feed: DataFeedPort,
    calc: FeatureCalcPort,
    planner: PlanBuilderPort,
    feature_spec: Mapping[str, Mapping[str, Any]],
    plan_spec: Mapping[str, Any],
    symbols: Iterable[str],
    start: str | None = None,
    end: str | None = None,
    columns: Sequence[str] = ("open", "high", "low", "close", "volume"),
    timeframe: str | None = None,
    tz: str = "UTC",
) -> PipelineOutputDTO:
    """OHLCVを取得→features計算→plan構築の一連を実行して返す。"""
    ohlcv = load_ohlcv(
        feed,
        symbols,
        start=start,
        end=end,
        columns=columns,
        timeframe=timeframe,
        tz=tz,
    )
    bundle = calc.compute(ohlcv, feature_spec)
    plan = planner.build(plan_spec)
    return PipelineOutputDTO(features=bundle.features, plan=plan)
