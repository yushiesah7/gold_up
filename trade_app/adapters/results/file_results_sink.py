from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

import pandas as pd

from trade_app.domain.ports.results_sink import ResultsSinkPort


class FileResultsSinkAdapter(ResultsSinkPort):
    """DataFrame/JSON を Parquet/CSV/JSON に保存。戻り値は生成パス辞書。"""

    __responsibility__: ClassVar[str] = "研究結果のローカルファイル保存（将来S3/GCS差替え可）"
    __debt_reason__: ClassVar[dict[str, str]] = {
        "reason": "クラウド転送やDB蓄積は将来Adapterで拡張",
        "owner": "infra",
    }

    def write(
        self,
        table: pd.DataFrame,
        summary: Mapping[str, Any],
        base_dir: Path,
        experiment_name: str,
        *,
        fmt: str = "parquet",
        with_timestamp_dir: bool = True,
    ) -> Mapping[str, Path]:
        if fmt not in {"parquet", "csv", "both"}:
            raise ValueError("fmt must be 'parquet' | 'csv' | 'both'")

        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        root = base_dir / experiment_name / ts if with_timestamp_dir else base_dir / experiment_name
        root.mkdir(parents=True, exist_ok=True)

        paths: dict[str, Path] = {}
        # 表
        if fmt in {"parquet", "both"}:
            p = root / "folds.parquet"
            table.to_parquet(p, engine="pyarrow", index=False)
            paths["folds_parquet"] = p
        if fmt in {"csv", "both"}:
            p = root / "folds.csv"
            table.to_csv(p, index=False)
            paths["folds_csv"] = p
        # サマリ
        sp = root / "summary.json"
        sp.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        paths["summary_json"] = sp

        return paths
