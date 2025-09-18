from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yaml

from trade_app.adapters.vbtpro.backtest_adapter import VbtProBacktestAdapter
from trade_app.adapters.vbtpro.data_feed_adapter import VbtProDataFeedAdapter
from trade_app.apps.features.feature_calc import DefaultFeatureCalculator
from trade_app.apps.features.pipeline.plan_builder import DefaultPlanBuilder
from trade_app.apps.research.explorer.spec_binding import bind_params_to_spec
from trade_app.apps.research.orchestrator import run_single_backtest


def main() -> int:  # noqa: PLR0915 - スモーク用途のため許容
    spec_path = Path("configs/strategy/spec.yaml")
    if not spec_path.exists():
        print(f"spec not found: {spec_path}", file=sys.stderr)
        return 2

    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}

    features_spec = spec.get("features", {})
    universe = spec.get("universe", {})
    sessions = spec.get("sessions", [])
    run_params = spec.get("run_params", {})

    symbols = list(universe.get("symbols", ["EURUSD"]))
    timeframes = list(universe.get("timeframes", ["m15"]))
    timeframe = timeframes[0] if timeframes else None

    print("[smoke] symbols=", symbols)
    print("[smoke] timeframe=", timeframe)
    print("[smoke] sessions=", sessions)
    print("[smoke] run_params keys=", sorted(run_params.keys()))

    # テンプレートバインド（デフォルト値）
    default_params = {
        "rsi.length": 14,
        "sma.len": 20,
        "bb.window": 20,
        "bb.mult": 2.0,
        "entry.rsi_gt": 55,
        "exit.rsi_lt": 45,
    }
    bound_features = bind_params_to_spec(features_spec, default_params)
    # 確実に複数トレードを出すため、簡易プランを使用（session_active 前提 + close>0）
    simple_plan = {
        "preconditions": [{"op": "eq", "left": "session_active", "right": True}],
        # features に存在する列（sma_20）で常時エントリー相当を作る
        "entries": [{"op": "gt", "left": "sma_20", "right": 0}],
        "exits": [],
    }
    bound_plan = simple_plan

    feed = VbtProDataFeedAdapter()
    calc = DefaultFeatureCalculator()
    planner = DefaultPlanBuilder()
    backtester = VbtProBacktestAdapter()

    # 複数トレードを確実化するため、保持期間を短く
    run_params = {**run_params, "max_bars_hold": 5}
    # smokeではゲートの同時保有上限を外す（PFの複数建て挙動を見るため）
    run_params.pop("max_positions", None)

    res = run_single_backtest(
        feed=feed,
        calc=calc,
        planner=planner,
        backtester=backtester,
        feature_spec=bound_features,
        plan_spec=bound_plan,
        symbols=symbols,
        timeframe=timeframe,
        tz="UTC",
        params=run_params,
        entry_gate=None,
        entry_gate_context=None,
    )

    pf = res.get("portfolio")
    print("[smoke] result keys:", list(res.keys()))

    # Try to print basic PF info
    n_trades = None
    if hasattr(pf, "trades"):
        try:
            trades = pf.trades  # type: ignore[attr-defined]
            if hasattr(trades, "count"):
                n_trades = int(trades.count())
            elif hasattr(trades, "records"):
                rec = trades.records  # type: ignore[attr-defined]
                n_trades = int(rec.shape[0]) if hasattr(rec, "shape") else None
            # 先頭数件を表示
            try:
                if hasattr(trades, "records_readable"):
                    rr = trades.records_readable  # type: ignore[attr-defined]
                    print("[smoke] trades head:\n", rr.head() if hasattr(rr, "head") else rr)
            except Exception:
                pass
        except Exception as e:
            print("[smoke] trades info error:", e)

    eq = None
    if hasattr(pf, "equity"):
        try:
            eq = pf.equity  # type: ignore[attr-defined]
        except Exception:
            eq = None

    if isinstance(eq, pd.Series):
        print("[smoke] equity: ", float(eq.iloc[0]), "->", float(eq.iloc[-1]))

    print("[smoke] n_trades:", n_trades)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
