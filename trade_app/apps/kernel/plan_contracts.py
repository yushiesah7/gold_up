"""
純関数カーネルが受け取る Plan DSL の契約定義。

- 外部ライブラリへの依存はなく、標準ライブラリの typing のみを使用します。
- アダプタが YAML などの外部設定から構築できる、プリミティブでシリアライズ可能な
  構造 (TypedDict / Literal) のみを定義します。
- カーネル側 (decide_core.py) は本定義の値をそのまま受け取って評価します。

このファイルは小さく明示的で安定的に保ち、カーネルの churn を避けます。
"""

from __future__ import annotations

from typing import Literal, TypedDict

# 比較演算子および論理演算子の集合は最小限で明示的に保つ
ComparisonOp = Literal["<", "<=", ">", ">=", "==", "!="]
LogicalOp = Literal["and", "or", "xor"]


class AtomPredicate(TypedDict):
    type: Literal["atom"]
    feature: str  # features に存在する列名
    op: ComparisonOp
    value: float  # 数値しきい値との比較 (atom は単純に保つ)


class NotPredicate(TypedDict):
    type: Literal["not"]
    child: PredicateNode


class BinOpPredicate(TypedDict):
    type: Literal["binop"]
    left: PredicateNode
    op: LogicalOp
    right: PredicateNode


PredicateNode = AtomPredicate | NotPredicate | BinOpPredicate


class PredicateRule(TypedDict):
    kind: Literal["predicate"]
    expr: PredicateNode


class CrossRule(TypedDict):
    # クロス系: 左辺の特徴量を右辺 (特徴量名または定数) と比較します。
    # 未来参照を避けるため、前バーと当バーの関係に基づいて交差を定義します。
    kind: Literal["cross_over", "cross_under"]
    left: str  # 特徴量名
    right: str | float  # 特徴量名 (Series) もしくは定数しきい値


Rule = PredicateRule | CrossRule


class Plan(TypedDict, total=False):
    # ロングエントリのルール群。AND/OR で単一のブールマスクに結合。
    entries: list[Rule]
    entries_combine: Literal["and", "or"]

    # ショートエントリのルール群。
    short_entries: list[Rule]
    short_entries_combine: Literal["and", "or"]

    # イグジットのルール群。
    exits: list[Rule]
    exits_combine: Literal["and", "or"]
