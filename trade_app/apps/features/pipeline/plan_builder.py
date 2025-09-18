from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar

from trade_app.domain.dto.plan_models import Clause, Plan
from trade_app.domain.ports.plan_builder import PlanBuilderPort


class DefaultPlanBuilder(PlanBuilderPort):
    """
    辞書（YAML読込結果）→ Plan(DSL) への最小正規化。
    仕様:
      - Clause.op: {"gt","ge","lt","le","eq","between","cross_over","cross_under"}
      - pre_shift: 省略時は 1（前バー判定→次足Open 約定の契約）
      - entries / short_entries / exits の3ブロック
    """

    __responsibility__: ClassVar[str] = "辞書→Plan(DSL) 正規化（最小プリミティブのみ）"

    _allowed_ops: ClassVar[set[str]] = {
        "gt",
        "ge",
        "lt",
        "le",
        "eq",
        "between",
        "cross_over",
        "cross_under",
    }

    def build(self, spec_dict: Mapping[str, Any]) -> Plan:
        def _mk(items: list[Mapping[str, Any]] | None) -> list[Clause]:
            out: list[Clause] = []
            for i, it in enumerate(items or []):
                op = str(it.get("op", "")).lower()
                if op not in self._allowed_ops:
                    raise ValueError(f"unsupported op at index {i}: {op}")
                pre_shift = int(it.get("pre_shift", 1))
                c = Clause(
                    op=op,
                    left=str(it.get("left")),
                    right=it.get("right"),
                    pre_shift=pre_shift,
                )
                out.append(c)
            return out

        return Plan(
            entries=_mk(spec_dict.get("entries")),
            short_entries=_mk(spec_dict.get("short_entries")),
            exits=_mk(spec_dict.get("exits")),
            meta=dict(spec_dict.get("meta", {})),
        )


# 既存の簡易関数が必要ならラッパを残す
def build_plan_from_dict(spec: Mapping[str, Any]) -> Plan:
    return DefaultPlanBuilder().build(spec)
