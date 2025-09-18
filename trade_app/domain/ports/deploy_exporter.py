from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol


class DeployExporterPort(Protocol):
    """探索結果（summary.csv & lock群）→ デプロイ用設定(YAML)を生成して返す"""

    def export_configs(
        self,
        *,
        summary_csv: Path,
        out_dir: Path,
        spec_path: Path | None = None,
        ensemble: str = "best",  # まずは best のみ実装 / 将来: topk_mean, vote など
        top_k: int = 1,
    ) -> Sequence[Path]:
        """生成した YAML ファイルパス群を返す"""
        ...
