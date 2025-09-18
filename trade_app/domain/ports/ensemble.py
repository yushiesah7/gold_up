from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any


class EnsembleExporterPort(ABC):
    """最適化結果(lock群)からデプロイ用設定を生成する責務"""

    @abstractmethod
    def export(
        self,
        rows: Sequence[Mapping[str, Any]],
        *,
        mode: str,  # "topk_mean" or "vote"
        k: int,
        out_dir: str,
    ) -> list[str]:
        """生成したファイルパスのリストを返す。

        rows は summary.csv の 1 行（dict）相当（symbol/timeframe/session/
        lock_path/best_score など）を想定。
        """
        raise NotImplementedError
