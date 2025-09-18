from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

Params = Mapping[str, Any]
Space = Mapping[str, Mapping[str, Any]]


class SamplerPort(Protocol):
    """初期点サンプラー（Sobol/QMC）"""

    __responsibility__ = "探索初期点（分散の良いシード）を生成"

    def sample(self, space: Space, n: int, *, seed: int | None = None) -> Sequence[Params]: ...
