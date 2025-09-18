from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

from trade_app.adapters.results.deploy_exporter_file import FileDeployExporterAdapter


def test_exporter_generates_yaml_from_summary_and_lock(tmp_path: Path):
    # --- 準備: base spec（テンプレ入り） ---
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        yaml.safe_dump(
            {
                "features": {
                    "rsi_{{rsi.length}}": {
                        "kind": "rsi",
                        "on": "close",
                        "params": {"length": "{{rsi.length}}"},
                    }
                },
                "plan": {
                    "preconditions": [{"op": "eq", "left": "session_active", "right": True}],
                    "entries": [{"op": "gt", "left": "rsi_{{rsi.length}}", "right": 60}],
                    "exits": [{"op": "lt", "left": "rsi_{{rsi.length}}", "right": 40}],
                },
                "sessions": [
                    {
                        "name": "LONDON",
                        "type": "window",
                        "start": "08:00",
                        "end": "17:00",
                        "tz": "Europe/London",
                    }
                ],
                "portfolio": {"size": 1.0, "fees": 0.0002},
            },
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    # --- ダミー lock.json（best_params のみでOK） ---
    lock_dir = tmp_path / "runs"
    lock_dir.mkdir()
    lock_path = lock_dir / "spec.lock.json"
    lock_path.write_text(
        json.dumps({"best_params": {"rsi.length": 14}}, ensure_ascii=False),
        encoding="utf-8",
    )

    # --- summary.csv（status=ok の1行） ---
    sum_path = tmp_path / "summary.csv"
    pd.DataFrame.from_records(
        [
            {
                "symbol": "EURUSD",
                "timeframe": "h1",
                "session": "LONDON",
                "best_score": 0.123,
                "lock_path": str(lock_path),
                "status": "ok",
                "reason": "",
            }
        ]
    ).to_csv(sum_path, index=False)

    # --- 実行 ---
    out_dir = tmp_path / "deploy"
    paths = FileDeployExporterAdapter().export_configs(
        summary_csv=sum_path,
        out_dir=out_dir,
        spec_path=spec,
    )

    assert len(paths) == 1
    out_file = paths[0]
    assert out_file.exists()

    doc = yaml.safe_load(out_file.read_text(encoding="utf-8"))
    # テンプレが置換されていること
    assert "rsi_14" in doc["features"]
    assert any(cond.get("left") == "rsi_14" for cond in doc["plan"]["entries"])  # type: ignore[index]
    # セッションが注入されていること
    assert doc["session"]["name"] == "LONDON"
    # ポートフォリオが引き継がれていること
    assert doc["portfolio"]["size"] == 1.0


def test_exporter_ignores_non_ok_rows(tmp_path: Path):
    sum_path = tmp_path / "summary.csv"
    pd.DataFrame.from_records(
        [
            {
                "symbol": "EURUSD",
                "timeframe": "h1",
                "session": "LONDON",
                "best_score": None,
                "lock_path": "",
                "status": "skipped",
                "reason": "no data",
            }
        ]
    ).to_csv(sum_path, index=False)

    out_dir = tmp_path / "deploy"
    paths = FileDeployExporterAdapter().export_configs(
        summary_csv=sum_path,
        out_dir=out_dir,
        spec_path=None,  # 使われない
    )
    assert paths == []
