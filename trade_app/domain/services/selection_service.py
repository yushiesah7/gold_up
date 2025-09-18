from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SelectionCriteria:
    min_sharpe: float = 1.0
    min_compounded: float = 0.0
    min_folds: int = 3
    min_trades: int | None = None  # ない場合は無視
    max_left_tail: float | None = None  # 例: -0.02 以下はNG


@dataclass(frozen=True)
class Candidate:
    symbol: str
    timeframe: str
    session: str
    lock_path: str
    summary: Mapping[str, Any]
    best_params: Mapping[str, Any]
    run_params: Mapping[str, Any] | None


def _get_num(d: Mapping[str, Any], *path: str) -> float | None:
    cur: Any = d
    for k in path:
        if not isinstance(cur, Mapping) or k not in cur:
            return None
        cur = cur[k]
    try:
        return float(cur)
    except Exception:
        return None


def passes_criteria(c: Candidate, criteria: SelectionCriteria) -> bool:
    s = c.summary or {}
    sharpe = _get_num(s, "mean", "sharpe_ratio") or 0.0
    compounded = _get_num(s, "compounded") or 0.0
    folds = int(s.get("folds", 0) or 0)
    left_tail = _get_num(s, "left_tail")

    if sharpe < criteria.min_sharpe:
        return False
    if compounded < criteria.min_compounded:
        return False
    if folds < criteria.min_folds:
        return False
    if criteria.max_left_tail is not None and left_tail is not None:
        if left_tail < criteria.max_left_tail:  # 左尾が深すぎる
            return False
    # min_trades は将来の拡張（ログに件数があれば対応）
    return True


def select_top_by_symbol_session(
    candidates: Iterable[Candidate], criteria: SelectionCriteria
) -> list[Candidate]:
    """symbol×session 単位で最良1件を返す。

    ソートキー優先度（降順の良し悪し）:
    - sharpe_ratio（高いほど良い）
    - compounded（高いほど良い）
    - right_tail（高いほど良い）
    - worst_month（高いほど良い）
    """
    from collections import defaultdict

    buckets: dict[tuple[str, str], list[Candidate]] = defaultdict(list)
    for c in candidates:
        if passes_criteria(c, criteria):
            buckets[(c.symbol, c.session)].append(c)

    def keyfn(c: Candidate) -> tuple[float, float, float, float]:
        s = c.summary or {}
        sharpe = _get_num(s, "mean", "sharpe_ratio") or 0.0
        compounded = _get_num(s, "compounded") or 0.0
        right_tail = _get_num(s, "right_tail") or 0.0
        worst_month = _get_num(s, "worst_month") or -1e9
        return (sharpe, compounded, right_tail, worst_month)

    out: list[Candidate] = []
    for _, arr in buckets.items():
        arr.sort(key=keyfn, reverse=True)
        if arr:
            out.append(arr[0])
    return out
