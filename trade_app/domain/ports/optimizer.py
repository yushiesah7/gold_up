from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any, Protocol

Params = Mapping[str, Any]
Space = Mapping[str, Mapping[str, Any]]
TrialRecord = Mapping[str, Any]
ObjectiveFn = Callable[[Params], float]


class OptimizerPort(Protocol):
    """パラメ探索の抽象（裏はOptuna/独自どちらでも）"""

    __responsibility__ = "空間Spaceと目的関数から最良パラメータを探索"

    def optimize(
        self,
        objective: ObjectiveFn,
        space: Space,
        *,
        n_trials: int,
        timeout_sec: int | None = None,
        seed: int | None = None,
        initial_points: Sequence[Params] | None = None,
    ) -> tuple[Params, float, list[TrialRecord]]: ...
