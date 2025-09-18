from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from trade_app.apps.research.metrics.aggregator import aggregate_wfa_results
from trade_app.apps.research.metrics.enricher import enrich_result
from trade_app.apps.research.orchestrator import run_wfa
from trade_app.domain.ports.backtest import BacktestPort
from trade_app.domain.ports.data_feed import DataFeedPort
from trade_app.domain.ports.feature_calc import FeatureCalcPort
from trade_app.domain.ports.plan_builder import PlanBuilderPort
from trade_app.domain.ports.results_sink import ResultsSinkPort
from trade_app.domain.ports.split_strategy import SplitStrategyPort


def run_wfa_and_save(
    *,
    feed: DataFeedPort,
    calc: FeatureCalcPort,
    planner: PlanBuilderPort,
    backtester: BacktestPort,
    splitter: SplitStrategyPort,
    feature_spec: Mapping[str, Mapping[str, Any]],
    plan_spec: Mapping[str, Any],
    symbols: Iterable[str],
    full_start: pd.Timestamp,
    full_end: pd.Timestamp,
    sink: ResultsSinkPort,
    base_dir: Path,
    experiment_name: str,
    timeframe: str | None = None,
    tz: str = "UTC",
    params: Mapping[str, Any] | None = None,
    rf: float = 0.0,
    fmt: str = "parquet",
) -> Mapping[str, Any]:
    """WFA実行→メトリクス付加→集約→保存。保存パスも返す。"""
    results = run_wfa(
        feed=feed,
        calc=calc,
        planner=planner,
        backtester=backtester,
        splitter=splitter,
        feature_spec=feature_spec,
        plan_spec=plan_spec,
        symbols=symbols,
        full_start=full_start,
        full_end=full_end,
        timeframe=timeframe,
        tz=tz,
        params=params,
    )
    enriched = [enrich_result(r, rf=rf) for r in results]
    table, summary = aggregate_wfa_results(enriched)
    paths = sink.write(table, summary, base_dir=base_dir, experiment_name=experiment_name, fmt=fmt)
    return {"table": table, "summary": summary, "paths": paths}
