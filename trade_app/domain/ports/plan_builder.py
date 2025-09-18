from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from trade_app.domain.dto.plan_models import Plan


class PlanBuilderPort(Protocol):
    """YAML/辞書→Plan(DSL)への正規化"""

    __responsibility__ = "planの構築（純関数に渡る最小プリミティブへ）"

    def build(self, spec_dict: Mapping[str, Any]) -> Plan: ...
