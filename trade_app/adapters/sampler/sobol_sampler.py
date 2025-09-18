from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import numpy as np

from trade_app.domain.ports.sampler import Params, SamplerPort, Space


def _unit_to_params(u: np.ndarray, space: Space) -> Params:
    """[0,1]^d の値を Space 型に落とす"""
    out: dict[str, Any] = {}
    keys = list(space.keys())
    for i, name in enumerate(keys):
        cfg = space[name]
        t = str(cfg.get("type", "float"))
        if t == "float":
            low, high = float(cfg["low"]), float(cfg["high"])  # type: ignore[index]
            val = low + (high - low) * float(u[i])
            step = cfg.get("step")
            if step:
                val = round(val / float(step)) * float(step)
            out[name] = float(val)
        elif t == "int":
            low, high = int(cfg["low"]), int(cfg["high"])  # type: ignore[index]
            val = low + math.floor((high - low + 1) * float(u[i]))
            step = int(cfg.get("step", 1))
            val = low + ((val - low) // step) * step
            val = min(max(val, low), high)
            out[name] = int(val)
        elif t == "categorical":
            choices = list(cfg["choices"])  # type: ignore[index]
            idx = math.floor(len(choices) * float(u[i]) - 1e-9)  # intのキャストを書き換えた
            idx = min(max(idx, 0), len(choices) - 1)
            out[name] = choices[idx]
        else:
            raise ValueError(f"unknown param type: {t}")
    return out


class SobolSamplerAdapter(SamplerPort):
    """
    Sobol/QMC の初期点生成。
    - scipy.stats.qmc.Sobol があれば使用、なければ Halton 近似にフォールバック。
    - どちらも [0,1]^d を生成し、Spaceへマッピング。
    """

    def sample(self, space: Space, n: int, *, seed: int | None = None) -> Sequence[Params]:
        d = len(space)
        if d == 0 or n <= 0:
            return []
        # 1) Scipy Sobol（任意）
        try:  # pragma: no cover - 環境依存
            from scipy.stats import qmc  # noqa: PLC0415

            eng = qmc.Sobol(d=d, scramble=True, seed=seed)
            u = eng.random(n)
        except Exception:
            # 2) Haltonフォールバック（素数基底）
            rng = np.random.default_rng(seed)
            primes = self._first_primes(d)
            cols = [self._van_der_corput(n, base=b, rng=rng) for b in primes]
            u = np.column_stack(cols)
        return [_unit_to_params(u[i], space) for i in range(n)]

    @staticmethod
    def _first_primes(k: int) -> list[int]:
        out: list[int] = []
        x = 2
        while len(out) < k:
            for p in out:
                if x % p == 0:
                    break
            else:
                out.append(x)
            x += 1
        return out

    @staticmethod
    def _van_der_corput(n: int, base: int, rng: np.random.Generator) -> np.ndarray:
        seq = np.zeros(n)
        for i in range(n):
            x, f = i + 1, 1.0 / base
            r = 0.0
            while x > 0:
                r += (x % base) * f
                x //= base
                f /= base
            seq[i] = r
        shift = rng.random()
        return (seq + shift) % 1.0
