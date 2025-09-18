from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

from trade_app.apps.features.pipeline.run_pipeline_full import run_pipeline_full
from trade_app.apps.research.policies.entry_gate import CombinedEntryGate
from trade_app.domain.ports.backtest import BacktestPort
from trade_app.domain.ports.data_feed import DataFeedPort
from trade_app.domain.ports.entry_gate import EntryGatePort
from trade_app.domain.ports.feature_calc import FeatureCalcPort
from trade_app.domain.ports.plan_builder import PlanBuilderPort
from trade_app.domain.ports.split_strategy import SplitStrategyPort
from trade_app.domain.services.decider import decide
from trade_app.utils.timing import build_logger, time_phase


def run_single_backtest(
    *,
    feed: DataFeedPort,
    calc: FeatureCalcPort,
    planner: PlanBuilderPort,
    backtester: BacktestPort,
    feature_spec: Mapping[str, Mapping[str, Any]],
    plan_spec: Mapping[str, Any],
    symbols: Iterable[str],
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
    timeframe: str | None = None,
    tz: str = "UTC",
    params: Mapping[str, Any] | None = None,
    entry_gate: EntryGatePort | None = None,
    entry_gate_context: Mapping[str, Any] | None = None,
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
        timeframe=timeframe,
        tz=tz,
    )
    log = build_logger()
    with time_phase(log, "decide"):
        sig = decide(pipe.features, pipe.plan)
    entries_to_use = sig.entries
    exits_to_use = sig.exits
    # オプトイン: params に max_positions があり、
    # 明示 entry_gate がない場合は CombinedEntryGate を適用
    auto_gate = None
    if entry_gate is None and isinstance(params, Mapping) and "max_positions" in params:
        try:
            auto_gate = CombinedEntryGate()
        except Exception:
            auto_gate = None
    gate_to_use = entry_gate or auto_gate
    if gate_to_use is not None:
        ctx = dict(entry_gate_context or {})
        if isinstance(params, Mapping) and "max_positions" in params:
            ctx.setdefault("max_positions", params["max_positions"])  # params優先
        entries_to_use = gate_to_use.gate(
            entries=sig.entries,
            exits=sig.exits,
            features=pipe.features,
            context=ctx,
        )
    with time_phase(log, "portfolio"):
        return backtester.run_from_signals(
            pipe.ohlcv, entries_to_use, exits_to_use, params=params or {}
        )


def run_wfa(
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
    timeframe: str | None = None,
    tz: str = "UTC",
    params: Mapping[str, Any] | None = None,
    entry_gate: EntryGatePort | None = None,
    entry_gate_context: Mapping[str, Any] | None = None,
) -> list[Mapping[str, Any]]:
    # フル期間を一度読み、Index を基に OOS 分割を作る（PFは全期間で1回だけ構築）
    pipe_full = run_pipeline_full(
        feed=feed,
        calc=calc,
        planner=planner,
        feature_spec=feature_spec,
        plan_spec=plan_spec,
        symbols=symbols,
        start=full_start,
        end=full_end,
        timeframe=timeframe,
        tz=tz,
        run_params=params,
    )
    index = pipe_full.ohlcv.frame.index
    folds = splitter.split(index)

    # 1) シグナルを全期間で評価
    sig = decide(pipe_full.features, pipe_full.plan)
    entries = sig.entries.reindex(index).fillna(False)
    exits = sig.exits.reindex(index).fillna(False)

    # オプトイン: params に max_positions があり、
    # 明示 entry_gate がない場合は CombinedEntryGate を適用
    auto_gate = None
    if entry_gate is None and isinstance(params, Mapping) and "max_positions" in params:
        try:
            auto_gate = CombinedEntryGate()
        except Exception:
            auto_gate = None
    gate_to_use = entry_gate or auto_gate
    if gate_to_use is not None:
        ctx = dict(entry_gate_context or {})
        if isinstance(params, Mapping) and "max_positions" in params:
            ctx.setdefault("max_positions", params["max_positions"])  # params優先
        entries = gate_to_use.gate(
            entries=entries,
            exits=exits,
            features=pipe_full.features,
            context=ctx,
        )

    # 2) PF を全期間で1回だけ構築
    full_res = backtester.run_from_signals(
        pipe_full.ohlcv,
        entries,
        exits,
        params=params or {},
    )

    # 3) 各 fold では equity を区間スライスしてメトリクス化
    #    enrich_result 側で sharpe 等を補完するため、equity_curve を渡す。
    #    scorer は summary['mean'] から sharpe_ratio/total_return を拾う。
    eq_full = None
    if isinstance(full_res.get("equity_curve"), pd.Series):
        eq_full = full_res["equity_curve"]
    elif "portfolio" in full_res and hasattr(full_res["portfolio"], "equity"):
        eq_full = full_res["portfolio"].equity  # type: ignore[assignment]

    results: list[Mapping[str, Any]] = []
    for oos_start, oos_end in folds:
        # 境界が不正（NaN/型不一致）の場合はスキップ
        try:
            valid = isinstance(oos_start, pd.Timestamp) and isinstance(oos_end, pd.Timestamp)
            if not valid:
                continue
            if pd.isna(oos_start) or pd.isna(oos_end):
                continue
        except Exception:
            continue
        rec: dict[str, Any] = {"oos_start": oos_start, "oos_end": oos_end}
        if eq_full is not None:
            # loc では NaN/存在しないラベルで落ちることがあるため、nearest indexer を用いて iloc スライスに変換
            try:
                idx = eq_full.index
                # 近傍インデクサ（見つからなければ -1）
                s_arr = idx.get_indexer([oos_start], method="nearest")
                e_arr = idx.get_indexer([oos_end], method="nearest")
                s_i = int(s_arr[0]) if len(s_arr) else -1
                e_i = int(e_arr[0]) if len(e_arr) else -1
                if s_i < 0 or e_i < 0 or e_i < s_i:
                    # このfoldはスキップ
                    results.append(rec)
                    continue
                # iloc で安全にスライス
                eq_slice = eq_full.iloc[s_i : e_i + 1]
            except Exception:
                # フォールバックとして loc を試す（失敗したらスキップ）
                try:
                    eq_slice = eq_full.loc[oos_start:oos_end]
                except Exception:
                    results.append(rec)
                    continue
            rec["equity_curve"] = eq_slice
            # 最小本数ガード：splitter.test_size の60%未満はスキップ（属性が無ければ閾値=5）
            try:
                test_size = int(getattr(splitter, "test_size", 0))
            except Exception:
                test_size = 0
            min_needed = max(5, int(test_size * 0.6)) if test_size > 0 else 5
            if len(eq_slice) < min_needed:
                results.append(rec)
                continue
            # total_return をトップレベルで添付（enricher が metrics に畳み込む）
            try:
                if len(eq_slice) >= 2:  # noqa: PLR2004
                    start_v = float(eq_slice.iloc[0])
                    end_v = float(eq_slice.iloc[-1])
                    rec["total_return"] = (end_v / start_v - 1.0) if start_v > 0.0 else 0.0
                else:
                    rec["total_return"] = 0.0
            except Exception:
                rec["total_return"] = 0.0
        else:
            # equity が無い環境でも破綻しないよう最小情報のみ
            rec["metrics"] = {}
        results.append(rec)
    return results
