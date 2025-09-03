from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, field_validator


class Timeframe(str, Enum):
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"


class Symbol(BaseModel):
    value: str

    @field_validator("value")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("symbol must be non-empty")
        return v
