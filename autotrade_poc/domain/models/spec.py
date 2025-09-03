from __future__ import annotations

import re
from zoneinfo import ZoneInfo

from pydantic import BaseModel, field_validator

from .market import Symbol, Timeframe
from .stops import StopMode, ATRRRSpec
from .risk import RiskPolicy
from .ensemble import EnsembleSpec

HHMM_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class ExecutionSpec(BaseModel):
    order_type: str  # "market" 等
    price: str  # "nextopen" 等
    slippage_rate: float
    fees_rate: float
    size: float
    leverage: float
    init_cash: float


class SessionConstraint(BaseModel):
    timezone: str
    start: str  # "HH:MM"
    end: str  # "HH:MM"

    @field_validator("start", "end")
    @classmethod
    def _validate_hhmm(cls, v: str) -> str:
        if not HHMM_RE.match(v):
            raise ValueError("time must be in HH:MM (00-23:59)")
        return v

    @field_validator("timezone")
    @classmethod
    def _validate_timezone(cls, v: str) -> str:
        # Ensure timezone is a valid IANA name
        try:
            ZoneInfo(v)
        except Exception as e:
            raise ValueError(f"invalid timezone: {v}") from e
        return v


class Constraints(BaseModel):
    session: SessionConstraint | None = None


class BrokerSpecs(BaseModel):
    digits: int
    point: float
    trade_contract_size: float
    trade_tick_value: float
    trade_tick_size: float
    volume_min: float
    volume_step: float
    trade_stops_level: int
    trade_freeze_level: int
    filling_mode: int
    spread: int


class LiveSpec(BaseModel):
    # YAMLのトップ構造をほぼそのままDTO化
    market_symbol: Symbol
    market_timeframe: Timeframe

    ensemble: EnsembleSpec
    execution: ExecutionSpec
    stops_mode: StopMode
    stops_atr_rr: ATRRRSpec | None = None

    risk: RiskPolicy
    constraints: Constraints | None = None
    broker_specs: BrokerSpecs | None = None
