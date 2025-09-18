from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from trade_app.domain.ports.ensemble import EnsembleExporterPort


class SimpleEnsembleExporter(EnsembleExporterPort):
    """summary.csv → lock_path を辿り、アンサンブル記述子を生成する実装。

    実際の平均/投票の“合成ロジック”は実行系（ランタイム）で解釈する前提。
    ここでは descriptor（.deploy.json）を作るだけに留め、疎結合を保つ。
    """

    def export(
        self,
        rows: Sequence[Mapping[str, Any]],
        *,
        mode: str,
        k: int,
        out_dir: str,
    ) -> list[str]:
        out_paths: list[str] = []
        out_root = Path(out_dir)
        out_root.mkdir(parents=True, exist_ok=True)

        df = pd.DataFrame.from_records(list(rows))
        if df.empty:
            return out_paths
        df = df[df.get("status", "ok") == "ok"]
        if df.empty:
            return out_paths

        grp_cols = ["symbol", "timeframe", "session"]
        for (symbol, timeframe, session), g in df.groupby(grp_cols):
            g2 = g.sort_values("best_score", ascending=False).head(k)
            components: list[dict[str, Any]] = []
            for _, r in g2.iterrows():
                lock_path = Path(str(r.get("lock_path", "")))
                meta: dict[str, Any] = {}
                try:
                    with lock_path.open("r", encoding="utf-8") as f:
                        lock = json.load(f)
                    meta = {
                        "created_at": lock.get("created_at"),
                        "best_params": lock.get("best_params"),
                    }
                except Exception:
                    meta = {"error": "cannot_read_lock"}
                components.append(
                    {
                        "lock_path": str(lock_path),
                        "best_score": r.get("best_score"),
                        "lock_meta": meta,
                    }
                )
            desc = {
                "symbol": symbol,
                "timeframe": timeframe,
                "session": session,
                "ensemble": {"mode": mode, "k": k, "components": components},
            }
            out_file = out_root / f"{symbol}_{timeframe}_{session}.deploy.json"
            file_content = json.dumps(desc, ensure_ascii=False, indent=2)
            out_file.write_text(file_content, encoding="utf-8")
            out_paths.append(str(out_file))

        idx = out_root / "deploy_index.json"
        content = json.dumps({"files": out_paths}, ensure_ascii=False, indent=2)
        idx.write_text(content, encoding="utf-8")
        return out_paths
