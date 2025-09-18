from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from trade_app.apps.research.explorer.objective import build_objective
from trade_app.apps.research.explorer.spec_binding import bind_params_to_spec
from trade_app.apps.research.metrics.aggregator import aggregate_wfa_results
from trade_app.apps.research.metrics.enricher import enrich_result
from trade_app.apps.research.orchestrator import run_wfa
from trade_app.domain.ports.lock_sink import LockSinkPort
from trade_app.domain.ports.optimizer import OptimizerPort
from trade_app.domain.ports.sampler import SamplerPort, Space
from trade_app.domain.ports.scorer import ScorerPort


class DefaultScorer(ScorerPort):
    """summary['mean']['sharpe_ratio'] を優先。無ければ total_return."""

    def score(self, summary: Mapping[str, Any]) -> float:
        mean = summary.get("mean", {}) if isinstance(summary.get("mean", {}), dict) else {}
        for k in ("sharpe_ratio", "total_return"):
            v = mean.get(k)
            if isinstance(v, int | float):
                return float(v)
        return 0.0


class RobustScorer(ScorerPort):
    """
    実利寄りのロバストスコアラー。
    - 基本: Sharpe をベース
    - ペナルティ: 最大ドローダウン、fold間の Sharpe 分散
    - 最低トレード数: 下回る場合は強い減点
    スコア例: Sharpe - λ1 * max_dd - λ2 * sharpe_var - λ3 * trades_shortfall
    """

    def __init__(
        self,
        *,
        maxdd_weight: float = 0.5,
        var_weight: float = 0.25,
        min_trades: int = 30,
        trades_penalty: float = 1.0,
    ) -> None:
        self.maxdd_weight = float(maxdd_weight)
        self.var_weight = float(var_weight)
        self.min_trades = int(min_trades)
        self.trades_penalty = float(trades_penalty)

    def score(self, summary: Mapping[str, Any]) -> float:
        mean = summary.get("mean", {}) if isinstance(summary.get("mean", {}), dict) else {}
        by_fold = summary.get("by_fold", []) if isinstance(summary.get("by_fold", []), list) else []

        sharpe = mean.get("sharpe_ratio")
        if not isinstance(sharpe, int | float):
            sharpe = mean.get("total_return", 0.0)
        sharpe = float(sharpe or 0.0)

        max_dd = mean.get("max_drawdown")
        max_dd = float(max_dd) if isinstance(max_dd, int | float) else 0.0

        trades = mean.get("n_trades")
        trades = int(trades) if isinstance(trades, int | float) else 0

        # foldごとの sharpe 分散
        sharpe_vals: list[float] = []
        if isinstance(by_fold, list):
            for f in by_fold:
                if isinstance(f, dict):
                    v = f.get("sharpe_ratio")
                    if isinstance(v, int | float):
                        sharpe_vals.append(float(v))
        sharpe_var = float(pd.Series(sharpe_vals).var()) if sharpe_vals else 0.0

        # ペナルティ計算
        pen_dd = self.maxdd_weight * max(0.0, max_dd)
        pen_var = self.var_weight * max(0.0, sharpe_var)
        pen_tr = self.trades_penalty * max(0, self.min_trades - trades)

        return float(sharpe - pen_dd - pen_var - pen_tr)


def run_explorer(
    *,
    feed,
    calc,
    planner,
    backtester,
    splitter,
    features_spec: Mapping[str, Any],
    plan_spec: Mapping[str, Any],
    space: Space,
    symbols: Iterable[str],
    full_start: pd.Timestamp,
    full_end: pd.Timestamp,
    timeframe: str | None,
    tz: str = "UTC",
    sampler: SamplerPort,
    optimizer: OptimizerPort,
    lock_sink: LockSinkPort,
    out_dir: Path,
    n_init: int = 16,
    n_trials: int = 64,
    timeout_sec: int | None = None,
    seed: int | None = None,
    params_template: Mapping[str, Any] | None = None,
    run_params: Mapping[str, Any] | None = None,
    scorer: ScorerPort | None = None,
) -> Mapping[str, Any]:
    scorer = scorer or DefaultScorer()
    objective = build_objective(
        feed=feed,
        calc=calc,
        planner=planner,
        backtester=backtester,
        splitter=splitter,
        base_features_spec=features_spec,
        base_plan_spec=plan_spec,
        symbols=symbols,
        full_start=full_start,
        full_end=full_end,
        timeframe=timeframe,
        tz=tz,
        params_template=params_template or {},
        scorer=scorer,
        run_params=run_params,
    )

    initial_points = sampler.sample(space, n=n_init, seed=seed)
    best_params, best_score, trials = optimizer.optimize(
        objective,
        space,
        n_trials=n_trials,
        timeout_sec=timeout_sec,
        seed=seed,
        initial_points=initial_points,
    )
    # まれに最適化器が空の dict を返す実装があるため保険
    if not best_params and initial_points:
        scored = [(p, float(objective(p))) for p in initial_points]
        scored.sort(key=lambda x: x[1], reverse=True)
        best_params, best_score = scored[0]

    # lock 出力（specはベスト値で具現化）
    best_f = bind_params_to_spec(features_spec, best_params)
    best_p = bind_params_to_spec(plan_spec, best_params)
    # ベスト固定で1回だけWFAを実行し、summaryを作成
    summary: dict[str, Any] = {}
    try:
        # build objective と同等のフローで、ベストparamsでのみ実行
        results = run_wfa(
            feed=feed,
            calc=calc,
            planner=planner,
            backtester=backtester,
            splitter=splitter,
            feature_spec=best_f,
            plan_spec=best_p,
            symbols=symbols,
            full_start=full_start,
            full_end=full_end,
            timeframe=timeframe,
            tz=tz,
            params=run_params,
        )
        enriched = [enrich_result(r) for r in results]
        _table, summary_dict = aggregate_wfa_results(enriched)
        if isinstance(summary_dict, dict):
            summary = summary_dict  # fold平均, compounded, by_month など
    except Exception:
        # summary 生成に失敗してもロックは出力を継続
        summary = {}
    lock_path = lock_sink.write(
        best_params=best_params,
        best_score=best_score,
        features_spec=best_f,
        plan_spec=best_p,
        space=space,
        out_dir=out_dir,
        summary=summary,
    )

    return {
        "best_params": best_params,
        "best_score": best_score,
        "trials": trials,
        "lock_path": lock_path,
    }
