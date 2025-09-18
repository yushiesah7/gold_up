from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd

from trade_app.domain.dto.plan_models import Clause, Plan
from trade_app.domain.dto.signals import SignalsDTO

__all__ = ["decide"]


def _resolve_operand(value: Any, features: pd.DataFrame) -> pd.Series | float:
    """右辺が列名（str）ならSeries、数値ならそのままfloat。
    未知型はそのまま返し、上位で型エラーにさせる。"""
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        return features[str(value)]
    return value  # type: ignore[return-value]


def _op_to_bool(op: str, left: pd.Series, right: pd.Series | float) -> pd.Series:
    if isinstance(right, pd.Series):
        right = right.reindex(left.index)
    if op == "gt":
        return left > right
    if op == "ge":
        return left >= right
    if op == "lt":
        return left < right
    if op == "le":
        return left <= right
    if op == "eq":
        return left == right
    raise ValueError(f"unsupported binary op: {op}")


def _between(left: pd.Series, right: list | tuple, features: pd.DataFrame) -> pd.Series:
    # right は [low, high]（いずれも列名 or 数値）
    if not isinstance(right, list | tuple) or len(right) != 2:  # noqa: PLR2004
        raise ValueError("between.right must be [low, high]")
    lo = _resolve_operand(right[0], features)
    hi = _resolve_operand(right[1], features)
    if isinstance(lo, pd.Series):
        lo = lo.reindex(left.index)
    if isinstance(hi, pd.Series):
        hi = hi.reindex(left.index)
    return (left >= lo) & (left <= hi)


def _cross(kind: str, left: pd.Series, right: pd.Series | float) -> pd.Series:
    """cross_over: left crosses above right（前バー以下→当バー超え）
    cross_under: left crosses below right（前バー以上→当バー下回り）"""
    if isinstance(right, int | float):
        r_now = pd.Series(float(right), index=left.index)
    else:
        r_now = right.reindex(left.index)
    l_prev = left.shift(1)
    r_prev = r_now.shift(1)
    if kind == "cross_over":
        return (left > r_now) & (l_prev <= r_prev)
    if kind == "cross_under":
        return (left < r_now) & (l_prev >= r_prev)
    raise ValueError(f"unsupported cross op: {kind}")


def _eval_block(clauses: Iterable[Clause], features: pd.DataFrame) -> pd.Series:
    """複数ClauseはANDで合成。空なら全FalseのSeries。"""
    if not clauses:
        return pd.Series(False, index=features.index)
    acc: pd.Series | None = None
    for c in clauses:
        left = features[str(c.left)]
        if c.op in {"gt", "ge", "lt", "le", "eq"}:
            right = _resolve_operand(c.right, features)
            cond = _op_to_bool(c.op, left, right)
        elif c.op == "between":
            cond = _between(left, c.right, features)  # type: ignore[arg-type]
        elif c.op in {"cross_over", "cross_under"}:
            right = _resolve_operand(c.right, features)
            if not isinstance(right, pd.Series):
                right = pd.Series(float(right), index=left.index)
            cond = _cross(c.op, left, right)
        else:
            raise ValueError(f"unsupported op: {c.op}")

        # pre_shift n: n本前のバーで判定とみなす（次足Open約定との整合）
        shift_n = int(getattr(c, "pre_shift", 1))
        if shift_n:
            # NaN を作らず False で埋めることで FutureWarning（downcast）回避
            cond = cond.shift(shift_n, fill_value=False)
        # 念のため明示的に bool 化（NaN は上で発生しない想定）
        cond = cond.astype(bool)
        acc = cond if acc is None else (acc & cond)
    return acc if acc is not None else pd.Series(False, index=features.index)


def decide(features: pd.DataFrame, plan: Plan) -> SignalsDTO:
    """
    純関数：features と plan を受けて、entries/short_entries/exits のbool Seriesを返す。
    - 外部I/Oなし
    - features のIndex/長さに追従
    """
    entries = _eval_block(plan.entries, features)
    short_entries = _eval_block(plan.short_entries, features)
    exits = _eval_block(plan.exits, features)
    return SignalsDTO(entries=entries, short_entries=short_entries, exits=exits)
