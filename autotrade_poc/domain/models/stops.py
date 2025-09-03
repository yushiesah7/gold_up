from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class StopMode(str, Enum):
    ATR_RR = "atr_rr"


class ATRRRSpec(BaseModel):
    atr_window: list[int]
    k_for_sl: list[float]
    rr: list[float]
