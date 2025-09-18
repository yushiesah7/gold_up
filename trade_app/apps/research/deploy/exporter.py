from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from trade_app.adapters.yaml.spec_loader_yaml import YamlSpecLoader


@dataclass(frozen=True)
class DeployRecord:
    symbol: str
    timeframe: str
    session: str
    score: float
    lock_path: Path


def _load_summary(summary_csv: Path) -> list[DeployRecord]:
    df = pd.read_csv(summary_csv)
    df = df[(df["status"] == "ok") & df["lock_path"].notna()]
    out: list[DeployRecord] = []
    for _, r in df.iterrows():
        out.append(
            DeployRecord(
                symbol=str(r["symbol"]),
                timeframe=str(r["timeframe"]),
                session=str(r["session"]),
                score=float(r.get("best_score", 0.0) or 0.0),
                lock_path=Path(str(r["lock_path"])),
            )
        )
    return out


def _load_lock(lock_path: Path) -> dict[str, Any]:
    with lock_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _session_to_yaml_node(session_label: str) -> dict[str, Any]:
    # 例: "LONDON" / "NY" / "TOKYO" / "ALLDAY" などをプリセット名としてそのまま記録
    name = session_label.split()[0]
    return {"preset": name}


def _build_strategy_id(sym: str, tf: str, sess: str) -> str:
    s = sess.split()[0]
    return f"{sym}_{tf}_{s}".upper()


def build_deploy_yaml(
    *,
    summary_csv: Path,
    spec_path: Path | None = None,
    topk: int | None = None,
) -> dict[str, Any]:
    """summary.csv と lock 群からデプロイ用の YAML ツリー（dict）を構築して返す。

    安全運用: spec_path が与えられた場合は、features/plan は spec.yaml をベースにし、
    lock 内の features_spec/plan_spec は無視し、best_params のみを採用する。
    """
    rows = _load_summary(summary_csv)
    if not rows:
        raise FileNotFoundError(f"No records in {summary_csv}")

    # base（spec.yaml）
    base_features: dict[str, Any] | None = None
    base_plan: dict[str, Any] | None = None
    if spec_path is not None:
        base_features, base_plan = YamlSpecLoader().load(spec_path)

    # スコア降順 → TopK
    rows_sorted = sorted(rows, key=lambda r: r.score, reverse=True)
    if topk is not None and topk > 0:
        rows_sorted = rows_sorted[:topk]

    strategies: list[dict[str, Any]] = []
    for r in rows_sorted:
        lock = _load_lock(r.lock_path)
        # 安全運用: spec がある場合は base を使い、lock の features/plan は無視
        features_spec = (
            base_features if base_features is not None else lock.get("features_spec", {})
        )
        plan_spec = base_plan if base_plan is not None else lock.get("plan_spec", {})
        params = lock.get("best_params", {})

        st_id = _build_strategy_id(r.symbol, r.timeframe, r.session)
        strategies.append(
            {
                "id": st_id,
                "symbol": r.symbol,
                "timeframe": r.timeframe,
                "session": _session_to_yaml_node(r.session),
                "score": r.score,
                "features": features_spec,
                "plan": plan_spec,
                "params": params,
            }
        )

    root: dict[str, Any] = {
        "version": 1,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "base_tz": "UTC",
        "source": {
            "summary_csv": str(summary_csv),
            **({"spec": str(spec_path)} if spec_path else {}),
        },
        "strategies": strategies,
        "deploy": {
            "position_cap": "auto",
            "risk_model": {"type": "none"},
        },
    }
    return root


def write_yaml(obj: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            obj,
            f,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )
