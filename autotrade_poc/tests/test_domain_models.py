from __future__ import annotations

import pytest
from pydantic import ValidationError

from autotrade_poc.domain.models.market import Symbol, Timeframe
from autotrade_poc.domain.models.risk import RiskPolicy
from autotrade_poc.domain.models.spec import SessionConstraint


def test_symbol_must_not_be_empty() -> None:
    with pytest.raises(ValidationError):
        Symbol(value="")


def test_timeframe_contains_m15() -> None:
    assert Timeframe.M15.value == "M15"


def test_risk_policy_range() -> None:
    # OK
    RiskPolicy(per_trade_risk_pct=0.02)
    # NG: 下限/上限外
    with pytest.raises(ValidationError):
        RiskPolicy(per_trade_risk_pct=0.0)
    with pytest.raises(ValidationError):
        RiskPolicy(per_trade_risk_pct=0.5)


def test_session_constraint_valid_minimal() -> None:
    SessionConstraint(timezone="UTC", start="09:00", end="17:00")

def test_session_constraint_invalid_format_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        SessionConstraint(timezone="UTC", start="9am", end="5pm")
