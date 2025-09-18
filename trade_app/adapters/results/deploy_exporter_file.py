from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from trade_app.adapters.yaml.spec_loader_yaml import YamlSpecLoader
from trade_app.apps.research.explorer.objective import bind_params_to_spec
from trade_app.domain.ports.deploy_exporter import DeployExporterPort


def _slug(s: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(s)).strip("_")


def _load_lock(lock_path: Path) -> Mapping[str, Any]:
    with lock_path.open("r", encoding="utf-8") as f:
        return json.load(f) or {}


def _select_session(sessions: list[Mapping[str, Any]] | None, label: str) -> Mapping[str, Any]:
    """summary.csv の 'session' は name か 'TZ start-end' ラベル。
    まず name 一致で拾い、無ければ name=label の簡易辞書にフォールバック。
    """
    if sessions:
        for sess in sessions:
            if str(sess.get("name", "")).lower() == str(label).lower():
                return dict(sess)
    return {"name": label}


class FileDeployExporterAdapter(DeployExporterPort):
    """summary.csv を読み、各行の lock.json の best_params を
    base spec にバインド → デプロイYAML出力"""

    def export_configs(
        self,
        *,
        summary_csv: Path,
        out_dir: Path,
        spec_path: Path | None = None,
        ensemble: str = "best",
        top_k: int = 1,
    ) -> Sequence[Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        df = pd.read_csv(summary_csv)
        # 対象は status == ok のみ
        df_ok = df[(df["status"] == "ok") & df["lock_path"].notna() & (df["lock_path"] != "")]
        if df_ok.empty:
            return []

        # base spec（features/plan/sessions/portfolio）を spec_path 優先でロード
        base_features: Mapping[str, Any] | None = None
        base_plan: Mapping[str, Any] | None = None
        base_sessions: list[Mapping[str, Any]] | None = None
        base_portfolio: Mapping[str, Any] | None = None
        if spec_path:
            features_spec, plan_spec = YamlSpecLoader().load(spec_path)
            base_features = features_spec
            base_plan = plan_spec
            with spec_path.open("r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            base_sessions = raw.get("sessions") or None
            base_portfolio = raw.get("portfolio") or None

        created: list[Path] = []

        for _, row in df_ok.iterrows():
            sym = str(row["symbol"])
            tf = str(row["timeframe"])
            session_label = str(row["session"])
            lock_path = Path(row["lock_path"])
            if not lock_path.is_absolute():
                lock_path = (summary_csv.parent / lock_path).resolve()

            lock = _load_lock(lock_path)
            # 安全運用: spec_path が指定された場合は常に base(spec.yaml) を使用し、
            # lock 内の features_spec/plan_spec は無視する
            if base_features is not None and base_plan is not None:
                features_spec = base_features
                plan_spec = base_plan
            else:
                # spec_path が無い場合のみ、lock 内の埋め込みにフォールバック
                features_spec = lock.get("features_spec") or base_features
                plan_spec = lock.get("plan_spec") or base_plan
            if features_spec is None or plan_spec is None:
                raise ValueError(
                    "Base features/plan spec is missing. Provide spec_path or include them in lock."
                )

            params = lock.get("best_params")
            if not isinstance(params, dict) or not params:
                # trials から拾える場合もあるが、実務では best_params を前提にする
                raise ValueError(f"best_params not found in lock: {lock_path}")

            # パラメータをバインドして具体化
            f_spec_bound = bind_params_to_spec(features_spec, params)
            p_spec_bound = bind_params_to_spec(plan_spec, params)

            # セッションは spec の一覧から name で拾う（なければフォールバック）
            session_obj = _select_session(base_sessions, session_label)

            # portfolio は spec 側があれば引き継ぐ
            portfolio_cfg = base_portfolio or {}

            # YAML 出力
            doc = {
                "symbol": sym,
                "timeframe": tf,
                "session": session_obj,
                "features": f_spec_bound,
                "plan": p_spec_bound,
            }
            if portfolio_cfg:
                doc["portfolio"] = portfolio_cfg

            out_path = out_dir / sym / tf / f"{_slug(session_label)}.yaml"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(doc, f, sort_keys=False, allow_unicode=True)
            created.append(out_path)

        return created
