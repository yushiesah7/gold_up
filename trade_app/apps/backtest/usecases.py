from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, ClassVar

from trade_app.apps.features.pipeline.run_pipeline_full import run_pipeline_full
from trade_app.domain.ports.backtest import BacktestPort
from trade_app.domain.ports.data_feed import DataFeedPort
from trade_app.domain.ports.feature_calc import FeatureCalcPort
from trade_app.domain.ports.plan_builder import PlanBuilderPort

# features + plan から signals を生成（decide は純関数）
from trade_app.domain.services.decider import decide

__responsibility__: ClassVar[str] = "仕様（features/plan）からsignalsを作り、BacktestPortを実行"


def backtest_from_specs(
    *,
    feed: DataFeedPort,
    calc: FeatureCalcPort,
    planner: PlanBuilderPort,
    backtester: BacktestPort,
    feature_spec: Mapping[str, Mapping[str, Any]],
    plan_spec: Mapping[str, Any],
    symbols: Iterable[str],
    start: str | None = None,
    end: str | None = None,
    columns: Sequence[str] = ("open", "high", "low", "close", "volume"),
    timeframe: str | None = None,
    tz: str = "UTC",
    params: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    pipe = run_pipeline_full(
        feed=feed,
        calc=calc,
        planner=planner,
        feature_spec=feature_spec,
        plan_spec=plan_spec,
        symbols=symbols,
        start=start,
        end=end,
        columns=columns,
        timeframe=timeframe,
        tz=tz,
        run_params=params,
    )

    signals = decide(pipe.features, pipe.plan)

    # BacktestPort.run_from_signals に委譲
    return backtester.run_from_signals(
        pipe.ohlcv,
        entries=signals.entries,
        exits=signals.exits,
        params=params or {},
    )
