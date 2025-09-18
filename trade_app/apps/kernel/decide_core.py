"""
トレードシグナル判定のための純関数カーネル。

- 副作用なし(I/Oなし、乱数なし、グローバル状態なし)
- YAML / フレームワーク / 外部ライブラリの契約を一切知らない
- 入力はアダプタ/パイプライン層が構築したプリミティブな系列データとDSL(Plan)のみ
- 出力は `entries` / `short_entries` / `exits` の真偽Series(入力と同じIndex整合)

このモジュールは DDD + Hexagonal の方針に従い、コアは「値のみ」を受け取ります。
インジケータやアダプタの拡張はここを変更せずに外側の層で完結させることを意図します(OCP)。

契約の概要:
- decide(open_, high, low, close, features, plan) -> dict[str, pd.Series]
- features: 価格系列と厳密に同じIndexを持つ dict[str, pd.Series]
- plan: plan_contracts.Plan を参照(決定的に評価)

全ての計算は決定的で、入力からのみ導出されます。
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, TypedDict

import pandas as pd

from .plan_contracts import ComparisonOp, LogicalOp, Plan, PredicateNode


class Decisions(TypedDict):
    entries: pd.Series
    short_entries: pd.Series
    exits: pd.Series


@dataclass(frozen=True)
class EvalContext:
    index: pd.Index
    features: dict[str, pd.Series]


def _ensure_alignment(series_list: Iterable[pd.Series]) -> pd.Index:
    it = iter(series_list)
    try:
        first = next(it)
    except StopIteration as err:
        raise ValueError("At least one series is required to determine alignment") from err
    idx = first.index
    for s in it:
        if not s.index.equals(idx):
            raise ValueError("All input series must have the same index")
    return idx


def _bool_series(index: pd.Index, value: bool = False) -> pd.Series:
    return pd.Series([value] * len(index), index=index, dtype=bool)


def _apply_comparison(left: pd.Series, op: ComparisonOp, right: float | pd.Series) -> pd.Series:
    if isinstance(right, int | float):
        r = float(right)
        match op:
            case "<":
                return left < r
            case "<=":
                return left <= r
            case ">":
                return left > r
            case ">=":
                return left >= r
            case "==":
                return left == r
            case "!=":
                return left != r
    else:
        # Series 同士の比較(Indexは整合している前提)
        match op:
            case "<":
                return left < right
            case "<=":
                return left <= right
            case ">":
                return left > right
            case ">=":
                return left >= right
            case "==":
                return left == right
            case "!=":
                return left != right
    raise ValueError(f"Unsupported comparison op: {op}")


def _logical(a: pd.Series, op: LogicalOp, b: pd.Series) -> pd.Series:
    if a.dtype != bool:
        a = a.astype(bool)
    if b.dtype != bool:
        b = b.astype(bool)
    match op:
        case "and":
            return a & b
        case "or":
            return a | b
        case "xor":
            return a ^ b
    raise ValueError(f"Unsupported logical op: {op}")


def _eval_predicate(node: PredicateNode, ctx: EvalContext) -> pd.Series:
    if node["type"] == "atom":
        feature = node["feature"]
        op = node["op"]
        right = node["value"]
        if feature not in ctx.features:
            raise KeyError(f"Missing feature: {feature}")
        left = ctx.features[feature]
        return _apply_comparison(left, op, right)
    elif node["type"] == "not":
        child = _eval_predicate(node["child"], ctx)
        return ~child.astype(bool)
    elif node["type"] == "binop":
        a = _eval_predicate(node["left"], ctx)
        b = _eval_predicate(node["right"], ctx)
        return _logical(a, node["op"], b)
    else:
        raise ValueError(f"Unknown predicate node type: {node['type']}")


def _compile_rule(rule: Plan.Rule, ctx: EvalContext) -> pd.Series:
    """単一のルールを真偽マスクにコンパイルする。

    対応するルール種別:
    - predicate: features 上の任意の真偽式
    - cross_over: 左辺の特徴量が右辺（特徴量/定数）を上抜け
    - cross_under: 左辺の特徴量が右辺（特徴量/定数）を下抜け
    """
    kind = rule["kind"]
    if kind == "predicate":
        return _eval_predicate(rule["expr"], ctx)
    elif kind in ("cross_over", "cross_under"):
        left_name = rule["left"]
        right = rule["right"]
        if left_name not in ctx.features:
            raise KeyError(f"Missing feature: {left_name}")
        left = ctx.features[left_name]
        if isinstance(right, str):
            if right not in ctx.features:
                raise KeyError(f"Missing feature: {right}")
            right_series: pd.Series | float = ctx.features[right]
        else:
            right_series = float(right)

        # クロス(交差)判定の真偽マスクを構築
        if isinstance(right_series, pd.Series):
            prev_left = left.shift(1)
            prev_right = right_series.shift(1)
            if kind == "cross_over":
                return (prev_left <= prev_right) & (left > right_series)
            else:
                return (prev_left >= prev_right) & (left < right_series)
        else:
            prev_left = left.shift(1)
            thr = right_series
            if kind == "cross_over":
                return (prev_left <= thr) & (left > thr)
            else:
                return (prev_left >= thr) & (left < thr)
    else:
        raise ValueError(f"Unsupported rule kind: {kind}")


def _combine(masks: Iterable[pd.Series], how: Literal["and", "or"] = "and") -> pd.Series:
    masks = list(masks)
    if not masks:
        raise ValueError("At least one mask is required to combine")
    acc = masks[0].astype(bool)
    for m in masks[1:]:
        if how == "and":
            acc = acc & m.astype(bool)
        else:
            acc = acc | m.astype(bool)
    return acc


def decide(
    open_: pd.Series,
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    *,
    features: dict[str, pd.Series],
    plan: Plan,
) -> Decisions:
    """与えられた features と plan を評価してエントリ/イグジット信号を生成する。

    全ての Series は同一Indexで整合している必要があります。クロス系の判定は前バー参照
    (shift(1)) で行うため、先頭インデックスは自然に False になります。これにより、
    バックテスト/実行エンジン側の「前バーでの判定 → 次足のOpenで執行」という契約と整合します。
    """
    idx = _ensure_alignment([open_, high, low, close, *features.values()])
    ctx = EvalContext(index=idx, features=features)

    # Build signals according to plan sections
    if plan.get("entries"):
        entry_masks = [_compile_rule(r, ctx) for r in plan["entries"]]
        entries = _combine(entry_masks, how=plan.get("entries_combine", "and"))
    else:
        entries = _bool_series(idx, False)

    if plan.get("short_entries"):
        short_masks = [_compile_rule(r, ctx) for r in plan["short_entries"]]
        short_entries = _combine(short_masks, how=plan.get("short_entries_combine", "and"))
    else:
        short_entries = _bool_series(idx, False)

    if plan.get("exits"):
        exit_masks = [_compile_rule(r, ctx) for r in plan["exits"]]
        exits = _combine(exit_masks, how=plan.get("exits_combine", "or"))
    else:
        exits = _bool_series(idx, False)

    # Ensure dtype is bool
    return Decisions(
        entries=entries.astype(bool),
        short_entries=short_entries.astype(bool),
        exits=exits.astype(bool),
    )
