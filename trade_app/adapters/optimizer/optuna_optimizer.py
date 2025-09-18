from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from trade_app.domain.ports.optimizer import (
    ObjectiveFn,
    OptimizerPort,
    Params,
    Space,
    TrialRecord,
)


class OptunaOptimizerAdapter(OptimizerPort):
    """
    Optuna + ASHA のラッパ。
    - optuna を実行時 import（未導入環境では利用しない想定：テストはFakeで代替）
    - Space を optuna の distribution に変換し、初期点を enqueue
    """

    def __init__(self, *, pruner: str = "sha", seed: int | None = None) -> None:
        # pruner: "median" | "sha"
        self._pruner_name = (pruner or "sha").lower()
        self._seed = seed

    def optimize(
        self,
        objective: ObjectiveFn,
        space: Space,
        *,
        n_trials: int,
        timeout_sec: int | None = None,
        seed: int | None = None,
        initial_points: Sequence[Params] | None = None,
    ) -> tuple[Params, float, list[TrialRecord]]:
        import optuna  # pragma: no cover - 外部依存  # noqa: PLC0415

        def _params_from_trial(trial: optuna.trial.Trial) -> Params:
            params: dict[str, Any] = {}
            for name, cfg in space.items():
                t = str(cfg.get("type", "float"))
                if t == "float":
                    low, high = float(cfg["low"]), float(cfg["high"])  # type: ignore[index]
                    step = cfg.get("step")
                    if step is not None:
                        params[name] = trial.suggest_float(name, low, high, step=float(step))
                    else:
                        params[name] = trial.suggest_float(name, low, high)
                elif t == "int":
                    low, high = int(cfg["low"]), int(cfg["high"])  # type: ignore[index]
                    step = int(cfg.get("step", 1))
                    params[name] = trial.suggest_int(name, low, high, step=step)
                elif t == "categorical":
                    params[name] = trial.suggest_categorical(name, list(cfg["choices"]))  # type: ignore[index]
                else:
                    raise ValueError(f"unknown type: {t}")
            return params

        sampler = optuna.samplers.TPESampler(seed=seed if seed is not None else self._seed)
        if self._pruner_name in ("median", "medianpruner"):
            pruner = optuna.pruners.MedianPruner()
        else:
            pruner = optuna.pruners.SuccessiveHalvingPruner()
        study = optuna.create_study(direction="maximize", sampler=sampler, pruner=pruner)

        for p in initial_points or []:
            study.enqueue_trial(dict(p))

        def _obj(tr: optuna.trial.Trial) -> float:
            p = _params_from_trial(tr)
            return float(objective(p))

        study.optimize(_obj, n_trials=n_trials, timeout=timeout_sec)
        best = study.best_trial
        trials: list[TrialRecord] = [
            {"params": t.params, "value": t.value, "number": t.number} for t in study.trials
        ]
        return dict(best.params), float(best.value), trials
