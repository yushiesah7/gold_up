from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

from trade_app.apps.research.explorer.spec_binding import bind_params_to_spec
from trade_app.apps.research.metrics.aggregator import aggregate_wfa_results
from trade_app.apps.research.metrics.enricher import enrich_result
from trade_app.apps.research.orchestrator import run_wfa
from trade_app.domain.ports.entry_gate import EntryGatePort
from trade_app.domain.ports.scorer import ScorerPort


def build_objective(
    *,
    feed,
    calc,
    planner,
    backtester,
    splitter,
    base_features_spec: Mapping[str, Any],
    base_plan_spec: Mapping[str, Any],
    symbols: Iterable[str],
    full_start: pd.Timestamp,
    full_end: pd.Timestamp,
    timeframe: str | None,
    tz: str,
    params_template: Mapping[str, Any],
    scorer: ScorerPort,
    run_params: Mapping[str, Any] | None = None,
    entry_gate: EntryGatePort | None = None,
    entry_gate_context: Mapping[str, Any] | None = None,
):
    """
    params -> score の objective を作る。
    - params を spec に埋め込み → WFA 実行 → メトリクス付加＆集約 → scorerでスコア
    """

    def _objective(params: Mapping[str, Any]) -> float:
        merged = dict(params_template)
        merged.update(params)
        f_spec = bind_params_to_spec(base_features_spec, merged)
        pl_spec = bind_params_to_spec(base_plan_spec, merged)

        results = run_wfa(
            feed=feed,
            calc=calc,
            planner=planner,
            backtester=backtester,
            splitter=splitter,
            feature_spec=f_spec,
            plan_spec=pl_spec,
            symbols=symbols,
            full_start=full_start,
            full_end=full_end,
            timeframe=timeframe,
            tz=tz,
            params=run_params,
            entry_gate=entry_gate,
            entry_gate_context=entry_gate_context,
        )
        enriched = [enrich_result(r) for r in results]
        _table, summary = aggregate_wfa_results(enriched)
        return float(scorer.score(summary))

    return _objective
