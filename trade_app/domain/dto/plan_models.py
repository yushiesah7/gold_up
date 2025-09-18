from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Clause(BaseModel):
    op: Literal["gt", "ge", "lt", "le", "eq", "between", "cross_over", "cross_under"]
    left: str
    right: str | float | list[float] | tuple[float, float]
    pre_shift: int = 1  # 次足Open約定のための標準前提


class Plan(BaseModel):
    """最小プリミティブだけ（純関数側はこの形だけ読めれば良い）"""

    entries: list[Clause] = Field(default_factory=list)
    short_entries: list[Clause] = Field(default_factory=list)
    exits: list[Clause] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
