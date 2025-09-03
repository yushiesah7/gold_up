from __future__ import annotations

from pydantic import BaseModel, field_validator


class RiskPolicy(BaseModel):
    per_trade_risk_pct: float  # 例: 0.02

    @field_validator("per_trade_risk_pct")
    @classmethod
    def _range(cls, v: float) -> float:
        if not (0 < v <= 0.1):
            raise ValueError("per_trade_risk_pct must be (0, 0.1]")
        return v
