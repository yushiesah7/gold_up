from __future__ import annotations

from pathlib import Path
from typing import Annotated

import numpy as np
import pandas as pd
import typer
import yaml

from trade_app.adapters.optimizer.optuna_optimizer import OptunaOptimizerAdapter
from trade_app.adapters.results.lock_sink_file import FileLockSinkAdapter
from trade_app.adapters.sampler.sobol_sampler import SobolSamplerAdapter
from trade_app.adapters.universe.config_universe import ConfigUniverseAdapter
from trade_app.adapters.vbtpro.backtest_adapter import VbtProBacktestAdapter
from trade_app.adapters.vbtpro.data_feed_adapter import VbtProDataFeedAdapter
from trade_app.adapters.vbtpro.vbtpro_bindings import parquet_pull
from trade_app.adapters.yaml.spec_loader_yaml import YamlSpecLoader
from trade_app.apps.features.feature_calc import DefaultFeatureCalculator
from trade_app.apps.features.pipeline.plan_builder import DefaultPlanBuilder
from trade_app.apps.research.explorer.batch_runner import run_batch_explorer
from trade_app.apps.research.explorer.run_explorer import DefaultScorer
from trade_app.apps.research.splitters.purged_walkforward import (
    PurgedWalkForwardSplitter,
)
from trade_app.apps.research.splitters.walkforward import WalkForwardSplitter

app = typer.Typer(no_args_is_help=True)


@app.command()
def autotune(  # noqa: PLR0915
    spec: Annotated[Path, typer.Argument(help="features/plan/space を含む YAML")],
    out_dir: Annotated[Path, typer.Option("--out-dir", help="結果出力先")] = Path("./runs"),
    start: Annotated[str, typer.Option("--start", help="UTC開始 'YYYY-MM-DD'")] = ...,
    end: Annotated[str, typer.Option("--end", help="UTC終了 'YYYY-MM-DD'")] = ...,
    tz: Annotated[str, typer.Option("--tz", help="基準タイムゾーン")] = "UTC",
    n_init: Annotated[int, typer.Option("--n-init", help="初期点(Sobol)")] = 16,
    n_trials: Annotated[int, typer.Option("--n-trials", help="試行数(Optuna)")] = 64,
    max_workers: Annotated[
        int | None,
        typer.Option(
            "--max-workers",
            help="外側ループ並列度（symbols×TF×sessions）",
        ),
    ] = None,
    purge: Annotated[
        int, typer.Option("--purge", help="Purged 本数（テスト直前を学習から除外）")
    ] = 0,
    # --- search controls ---
    pruner: Annotated[
        str,
        typer.Option("--pruner", help="Optuna pruner: 'median' or 'sha'"),
    ] = "sha",
    scorer_name: Annotated[
        str,
        typer.Option("--scorer", help="Scorer: 'default' or 'robust'"),
    ] = "default",
    embargo: Annotated[
        int,
        typer.Option("--embargo", help="Embargo 本数（テスト直後の本数を次学習から除外）"),
    ] = 0,
    session_only: Annotated[
        str | None,
        typer.Option(
            "--session-only",
            help="""対象セッション名を限定（例: 'NY' or 'NY,LONDON'）。
            未指定ならspec.yamlの全セッション""",
        ),
    ] = None,
    # --- backtest run_params (コスト/サイズ/レバ/RR/ATR) ---
    fees: Annotated[float | None, typer.Option("--fees", help="片道コスト(比率)")] = None,
    slippage: Annotated[float | None, typer.Option("--slippage", help="スリッページ(比率)")] = None,
    size: Annotated[float | None, typer.Option("--size", help="発注サイズ(数量 or 比率)")] = None,
    init_cash: Annotated[float | None, typer.Option("--init-cash", help="初期資金")] = None,
    leverage: Annotated[float | None, typer.Option("--leverage", help="レバレッジ倍率")] = None,
    cash_sharing: Annotated[
        bool | None, typer.Option("--cash-sharing/--no-cash-sharing", help="資金共有")
    ] = None,
    size_type: Annotated[
        str | None, typer.Option("--size-type", help="vectorbtのsize_type指定")
    ] = None,
    sl_pct: Annotated[float | None, typer.Option("--sl-pct", help="損切(相対): 0.01=1%")] = None,
    tp_pct: Annotated[float | None, typer.Option("--tp-pct", help="利確(相対)")] = None,
    rr: Annotated[
        float | None, typer.Option("--rr", help="RR。tp_pct未指定なら tp=rr*sl_pct")
    ] = None,
    sl_atr_mult: Annotated[float | None, typer.Option("--sl-atr-mult", help="ATR倍の損切")] = None,
    tp_atr_mult: Annotated[float | None, typer.Option("--tp-atr-mult", help="ATR倍の利確")] = None,
    atr_window: Annotated[
        int | None, typer.Option("--atr-window", help="ATR期間(デフォ14)")
    ] = None,
    # --- exits ---
    max_bars_hold: Annotated[
        int | None,
        typer.Option("--max-bars-hold", help="エントリー後の最大保有バー数（経過後に強制Exit）"),
    ] = None,
    sl_trail: Annotated[
        bool | None,
        typer.Option("--sl-trail/--no-sl-trail", help="トレーリングストップ有効化"),
    ] = None,
    # --- auto range ---
    auto_range: Annotated[
        bool,
        typer.Option(
            "--auto-range/--no-auto-range",
            help="ATR分布とコストから探索レンジを自動生成してspaceにマージ",
        ),
    ] = False,
):
    """Universe×TF×Session で自動探索→lock.json を出力（最小CLI）"""
    # ---- spec 読み込み（features/plan/space）----
    features_spec, plan_spec = YamlSpecLoader().load(spec)
    with spec.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    space = raw.get("space") or (features_spec.pop("_space", {}) | plan_spec.pop("_space", {}))
    base_run_params = raw.get("run_params") or {}

    # ---- universe / sessions（spec.yamlにあれば優先、なければ既定）----
    uni_cfg = raw.get("universe")
    if isinstance(uni_cfg, dict):
        # 例: {symbols: [...], timeframes: [...]} の形を想定
        uni = ConfigUniverseAdapter(cfg=uni_cfg)
    else:
        uni = ConfigUniverseAdapter()
    sessions = raw.get("sessions") or [
        {"name": "ALLDAY", "type": "all", "tz": tz},
        {
            "name": "LONDON",
            "type": "window",
            "start": "08:00",
            "end": "17:00",
            "tz": "Europe/London",
        },
        {
            "name": "NY",
            "type": "window",
            "start": "09:30",
            "end": "16:00",
            "tz": "America/New_York",
        },
        {
            "name": "TOKYO",
            "type": "window",
            "start": "09:00",
            "end": "15:00",
            "tz": "Asia/Tokyo",
        },
    ]

    # --session-only のフィルタ適用（カンマ区切り許容）
    if session_only:
        wanted = {s.strip() for s in str(session_only).split(",") if s.strip()}
        sessions = [s for s in sessions if str(s.get("name")) in wanted]
        if not sessions:
            raise typer.BadParameter(
                f"--session-only に一致するセッションがありません: {session_only}"
            )

    # ---- auto-range: ATR 分布 + コストから動的に探索レンジを生成（不足キーのみ補完） ----
    if auto_range:
        try:
            # 対象の代表サンプル（先頭のシンボル/TF）で近似。重い処理を避けるため1つに限定。
            uni_tmp = (
                ConfigUniverseAdapter(cfg=uni_cfg)
                if isinstance(uni_cfg, dict)
                else ConfigUniverseAdapter()
            )
            symbols = list(uni_tmp.list_symbols())
            tfs = list(uni_tmp.list_timeframes())
            if symbols and tfs:
                sym0, tf0 = symbols[0], tfs[0]
                df = parquet_pull(
                    [sym0],
                    pd.Timestamp(start, tz="UTC"),
                    pd.Timestamp(end, tz="UTC"),
                    ["open", "high", "low", "close"],
                    tf0,
                    tz,
                )
                df = df.sort_index()
                # 単一シンボル列に正規化
                if isinstance(df.columns, pd.MultiIndex):
                    # 末尾レベルがシンボルになる想定
                    try:
                        df = df.xs(sym0, level=-1, axis=1)
                    except Exception:
                        df = df.droplevel(-1, axis=1)
                # ATR 相対（対 close）
                high, low, close = df["high"], df["low"], df["close"]
                prev_close = close.shift(1)
                tr = np.maximum(
                    (high - low).values,
                    np.maximum((high - prev_close).values, (low - prev_close).values),
                )
                tr_df = pd.Series(tr, index=close.index)
                w = int(atr_window or 14)
                atr = tr_df.ewm(alpha=1.0 / float(w), adjust=False, min_periods=w).mean()
                rel_atr = (atr / close.replace(0, np.nan)).fillna(0.0)
                med_rel = float(rel_atr.median()) if len(rel_atr) else 0.0
                # コスト（片道）合算の目安（利確下限）。安全側に少し上乗せ。
                cost = float(
                    (fees or base_run_params.get("fees") or 0.0)
                    + (slippage or base_run_params.get("slippage") or 0.0)
                )
                min_tp_pct = max(0.0, cost * 1.2)
                # 提案レンジ（不足キーのみ）
                if "sl_atr_mult" not in space:
                    space["sl_atr_mult"] = {"type": "float", "low": 0.8, "high": 1.8, "step": 0.1}
                if "tp_atr_mult" not in space:
                    # tp の下限を BE 超えに誘導
                    tp_min = 1.0 if med_rel == 0 else max(1.0, min_tp_pct / med_rel)
                    space["tp_atr_mult"] = {
                        "type": "float",
                        "low": round(tp_min, 2),
                        "high": 3.0,
                        "step": 0.1,
                    }
                if "rr" not in space:
                    space["rr"] = {"type": "float", "low": 1.2, "high": 3.0, "step": 0.1}
        except FileNotFoundError:
            # データがない場合は静かにスキップ（既定spaceのまま）
            pass

    # ---- DI: 実装束ね ----
    feed = VbtProDataFeedAdapter()
    calc = DefaultFeatureCalculator()
    planner = DefaultPlanBuilder()
    backtester = VbtProBacktestAdapter()
    base_splitter = WalkForwardSplitter(train_size=252 * 2, test_size=252 // 2)  # 例
    splitter = (
        PurgedWalkForwardSplitter(
            train_size=base_splitter.train_size,
            test_size=base_splitter.test_size,
            purge=purge,
            embargo=embargo,
        )
        if (purge > 0 or embargo > 0)
        else base_splitter
    )
    sampler = SobolSamplerAdapter()
    optimizer = OptunaOptimizerAdapter(pruner=pruner)
    sink = FileLockSinkAdapter()
    # scorer selection (robust is resolved in run_explorer import to avoid cycle)
    scorer = None
    if str(scorer_name).lower() == "robust":
        try:
            from trade_app.apps.research.explorer.run_explorer import RobustScorer  # noqa: PLC0415

            scorer = RobustScorer()
        except Exception:
            scorer = DefaultScorer()
    else:
        scorer = DefaultScorer()

    # ---- run_params（spec.yaml ベースに CLI で上書き）----
    rp = dict(base_run_params)
    overrides = dict(
        fees=fees,
        slippage=slippage,
        size=size,
        init_cash=init_cash,
        leverage=leverage,
        cash_sharing=cash_sharing,
        size_type=size_type,
        sl_pct=sl_pct,
        tp_pct=tp_pct,
        rr=rr,
        sl_atr_mult=sl_atr_mult,
        tp_atr_mult=tp_atr_mult,
        atr_window=atr_window,
        max_bars_hold=max_bars_hold,
        sl_trail=sl_trail,
    )
    for k, v in overrides.items():
        if v is not None:
            rp[k] = v

    # ---- 実行 ----
    table = run_batch_explorer(
        universe=uni,
        sessions=sessions,
        feed=feed,
        calc=calc,
        planner=planner,
        backtester=backtester,
        splitter=splitter,
        features_spec=features_spec,
        plan_spec=plan_spec,
        space=space,
        full_start=pd.Timestamp(start, tz="UTC"),
        full_end=pd.Timestamp(end, tz="UTC"),
        tz=tz,
        sampler=sampler,
        optimizer=optimizer,
        lock_sink=sink,
        out_dir=out_dir,
        n_init=n_init,
        n_trials=n_trials,
        max_workers=max_workers,
        run_params=rp,
        scorer=scorer,
    )
    out = out_dir / "summary.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(out, index=False)
    typer.echo(f"saved: {out}")


def main() -> None:  # pragma: no cover
    app()


@app.command()
def autotune_plan(
    spec: Annotated[Path, typer.Argument(help="features/plan/space を含む YAML")],
    plan: Annotated[Path, typer.Argument(help="ジョブ定義YAML（jobs: 配列）")],
    out_dir: Annotated[Path, typer.Option("--out-dir", help="ベース出力ディレクトリ")] = Path(
        "./runs"
    ),
    start: Annotated[str, typer.Option("--start", help="UTC開始 'YYYY-MM-DD'")] = ...,
    end: Annotated[str, typer.Option("--end", help="UTC終了 'YYYY-MM-DD'")] = ...,
    tz: Annotated[str, typer.Option("--tz", help="基準タイムゾーン")] = "UTC",
) -> None:
    """
    プランYAMLに列挙されたジョブ（セッション別・run_params上書き等）を順次実行。
    - 各ジョブの結果は out_dir/<job_name>/summary.csv に保存
    - 例のプランYAML:
        jobs:
          - name: NY_1
            session_only: NY
            n_init: 16
            n_trials: 128
            run_params: { sl_atr_mult: 1.0, tp_atr_mult: 2.2, atr_window: 14 }
    """
    # spec 読み
    features_spec, plan_spec = YamlSpecLoader().load(spec)
    with spec.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    space = raw.get("space") or (features_spec.pop("_space", {}) | plan_spec.pop("_space", {}))
    base_run_params = raw.get("run_params") or {}
    uni_cfg = raw.get("universe")
    uni = (
        ConfigUniverseAdapter(cfg=uni_cfg) if isinstance(uni_cfg, dict) else ConfigUniverseAdapter()
    )
    base_sessions = raw.get("sessions") or [
        {"name": "ALLDAY", "type": "all", "tz": tz},
        {
            "name": "LONDON",
            "type": "window",
            "start": "08:00",
            "end": "17:00",
            "tz": "Europe/London",
        },
        {
            "name": "NY",
            "type": "window",
            "start": "09:30",
            "end": "16:00",
            "tz": "America/New_York",
        },
        {"name": "TOKYO", "type": "window", "start": "09:00", "end": "15:00", "tz": "Asia/Tokyo"},
    ]

    # DI
    feed = VbtProDataFeedAdapter()
    calc = DefaultFeatureCalculator()
    planner = DefaultPlanBuilder()
    backtester = VbtProBacktestAdapter()
    splitter = WalkForwardSplitter(train_size=252 * 2, test_size=252 // 2)
    sampler = SobolSamplerAdapter()
    optimizer = OptunaOptimizerAdapter()
    sink = FileLockSinkAdapter()

    # プラン読込
    with plan.open("r", encoding="utf-8") as f:
        plan_raw = yaml.safe_load(f) or {}
    jobs = plan_raw.get("jobs") or []
    if not jobs:
        raise typer.BadParameter("plan に jobs が見つかりません")

    for j in jobs:
        jname = str(j.get("name") or "job")
        session_only = j.get("session_only")
        n_init = int(j.get("n_init", 16))
        n_trials = int(j.get("n_trials", 64))
        rp = dict(base_run_params)
        overrides = dict(j.get("run_params") or {})
        for k, v in overrides.items():
            if v is not None:
                rp[k] = v

        # セッション絞り込み
        sessions = base_sessions
        if session_only:
            wanted = {s.strip() for s in str(session_only).split(",") if s.strip()}
            sessions = [s for s in sessions if str(s.get("name")) in wanted]
            if not sessions:
                raise typer.BadParameter(f"plan.jobs[{jname}] session_only 不一致: {session_only}")

        table = run_batch_explorer(
            universe=uni,
            sessions=sessions,
            feed=feed,
            calc=calc,
            planner=planner,
            backtester=backtester,
            splitter=splitter,
            features_spec=features_spec,
            plan_spec=plan_spec,
            space=space,
            full_start=pd.Timestamp(start, tz="UTC"),
            full_end=pd.Timestamp(end, tz="UTC"),
            tz=tz,
            sampler=sampler,
            optimizer=optimizer,
            lock_sink=sink,
            out_dir=out_dir / jname,
            n_init=n_init,
            n_trials=n_trials,
            max_workers=None,
            run_params=rp,
        )
        out = out_dir / jname / "summary.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(out, index=False)
        typer.echo(f"saved: {out}")


if __name__ == "__main__":  # pragma: no cover
    # Register all commands above, then run Typer app
    app()
