from __future__ import annotations

from pydantic import BaseModel


class EnsembleColumn(BaseModel):
    label: str  # 例: "thr=|rsi=14|bb=(30, 1.75)"


class EnsembleSpec(BaseModel):
    columns: list[EnsembleColumn]
    weights: dict[str, float]
    meta: dict[str, str | int | float]
