from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from trade_app.apps.research.explorer.run_explorer import run_explorer
from trade_app.apps.research.splitters.purged_walkforward import (
    PurgedWalkForwardSplitter,
)
from trade_app.apps.research.splitters.walkforward import WalkForwardSplitter
from trade_app.domain.ports.lock_sink import LockSinkPort
from trade_app.domain.ports.optimizer import OptimizerPort
from trade_app.domain.ports.sampler import SamplerPort
from trade_app.domain.ports.scorer import ScorerPort
from trade_app.domain.ports.universe import UniversePort


def run_batch_explorer(  # noqa: PLR0915 - 外側制御の関数でステートメント多めを許容
    *,
    universe: UniversePort,
    sessions: Sequence[Mapping[str, Any]],
    feed,
    calc,
    planner,
    backtester,
    splitter,
    features_spec: Mapping[str, Any],
    plan_spec: Mapping[str, Any],
    space: Mapping[str, Any],
    full_start: pd.Timestamp,
    full_end: pd.Timestamp,
    tz: str,
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
    max_workers: int | None = None,
) -> pd.DataFrame:
    """
    外側ループ：symbols × timeframes × sessions を回して run_explorer を実行。
    戻り値はベストスコアの一覧テーブル（組合せごと1行）。
    注: run_explorer の I/F に合わせ、セッション情報は run_params 経由で受け渡し可能。
    """
    records: list[dict[str, Any]] = []
    symbols = list(universe.list_symbols())
    tfs = list(universe.list_timeframes())

    def _label_session(sess: Mapping[str, Any]) -> str:
        return sess.get("name") or (
            f"{sess.get('tz', 'UTC')} {sess.get('start', '00:00')}-{sess.get('end', '24:00')}"
        )

    # rolling_profiles.yaml を標準読み込み（存在すれば使用）
    profiles: dict[str, Any] = {}
    try:
        prof_path = Path("configs/strategy/rolling_profiles.yaml")
        if prof_path.exists():
            raw = yaml.safe_load(prof_path.read_text(encoding="utf-8")) or {}
            if isinstance(raw.get("profiles"), dict):
                profiles = raw["profiles"]
    except Exception:
        profiles = {}

    def _match_profile(tf_name: str, sess: Mapping[str, Any]) -> Mapping[str, Any] | None:
        """timeframe と セッション名に合致する最初のプロファイルを返す。"""
        if not profiles:
            return None
        sess_name = str(sess.get("name", "")).lower()
        tf_l = str(tf_name).lower()
        # 候補: {tf}_{sess} 形式 / {tf}_all
        keys = [
            f"{tf_l}_{sess_name}",
            f"{tf_l}_all",
        ]
        for k in keys:
            prof = profiles.get(k)
            if isinstance(prof, dict) and str(prof.get("timeframe", "")).lower() == tf_l:
                return prof
        # 直接一致（キーに依らず、timeframe一致＆name一致）も探索
        for prof in profiles.values():
            if not isinstance(prof, dict):
                continue
            if str(prof.get("timeframe", "")).lower() != tf_l:
                continue
            p_sess = prof.get("session_preset", {})
            if isinstance(p_sess, dict) and str(p_sess.get("name", "")).lower() == sess_name:
                return prof
        return None

    def _run_one(sym: str, tf: str, sess: Mapping[str, Any]) -> dict[str, Any]:
        rp = dict(run_params or {})
        # rolling_profiles 優先適用（無ければ従来既定）
        tf_l = str(tf).lower()
        prof = _match_profile(tf_l, sess)
        if isinstance(prof, Mapping):
            # session_preset をプロファイルから上書き
            p_sess = prof.get("session_preset")
            if isinstance(p_sess, Mapping):
                rp["session_preset"] = p_sess
            else:
                rp["session_preset"] = sess
            # 分割サイズ（purge/embargo は任意）
            train_bars = int(eval(str(prof.get("train_bars", 0))))
            test_bars = int(eval(str(prof.get("test_bars", 0))))
            purge_bars = int(eval(str(prof.get("purge_bars", 0))))
            embargo_bars = int(eval(str(prof.get("embargo_bars", 0))))
            if purge_bars > 0 or embargo_bars > 0:
                local_splitter = PurgedWalkForwardSplitter(
                    train_size=train_bars,
                    test_size=test_bars,
                    purge=max(0, purge_bars),
                    embargo=max(0, embargo_bars),
                )
            else:
                local_splitter = WalkForwardSplitter(train_size=train_bars, test_size=test_bars)
        else:
            # 従来の既定
            rp["session_preset"] = sess
            if tf_l == "h1":
                local_splitter = WalkForwardSplitter(train_size=24 * 90, test_size=24 * 30)
            elif tf_l == "m15":
                local_splitter = WalkForwardSplitter(train_size=24 * 4 * 90, test_size=24 * 4 * 45)
            elif tf_l == "h4":
                local_splitter = WalkForwardSplitter(train_size=6 * 90, test_size=6 * 30)
            else:
                local_splitter = splitter

        # 組合せごとの出力先（lockの上書き混同を回避）
        def _safe(s: str) -> str:
            return re.sub(r"[^A-Za-z0-9_\-]", "_", s)

        sess_label = _label_session(sess)
        combo_out_dir = out_dir / _safe(sym) / _safe(str(tf)) / _safe(sess_label)

        try:
            out = run_explorer(
                feed=feed,
                calc=calc,
                planner=planner,
                backtester=backtester,
                splitter=local_splitter,
                features_spec=features_spec,
                plan_spec=plan_spec,
                space=space,
                symbols=[sym],
                full_start=full_start,
                full_end=full_end,
                timeframe=tf,
                tz=tz,
                sampler=sampler,
                optimizer=optimizer,
                lock_sink=lock_sink,
                out_dir=combo_out_dir,
                n_init=n_init,
                n_trials=n_trials,
                timeout_sec=timeout_sec,
                seed=seed,
                params_template=params_template,
                run_params=rp,
                scorer=scorer,
            )
            return {
                "symbol": sym,
                "timeframe": tf,
                "session": sess_label,
                "best_score": out["best_score"],
                "lock_path": str(out["lock_path"]),
                "status": "ok",
                "reason": "",
            }
        except FileNotFoundError as e:
            return {
                "symbol": sym,
                "timeframe": tf,
                "session": _label_session(sess),
                "best_score": None,
                "lock_path": "",
                "status": "skipped",
                "reason": str(e),
            }

    if (max_workers or 0) > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [
                ex.submit(_run_one, sym, tf, sess)
                for sym in symbols
                for tf in tfs
                for sess in sessions
            ]
            for fut in as_completed(futures):
                records.append(fut.result())
    else:
        for sym in symbols:
            for tf in tfs:
                for sess in sessions:
                    records.append(_run_one(sym, tf, sess))

    return pd.DataFrame.from_records(records)
