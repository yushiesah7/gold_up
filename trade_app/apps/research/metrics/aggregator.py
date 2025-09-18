from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

TAIL_Q_HI: float = 0.95
TAIL_Q_LO: float = 0.05
MIN_TAIL_SAMPLES: int = 5


def _flatten_metrics(rec: Mapping[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    # oos期間情報を最優先で拾う
    for k in ("oos_start", "oos_end"):
        if k in rec:
            row[k] = rec[k]
    m = rec.get("metrics", {}) or {}
    if hasattr(m, "to_dict"):
        m = m.to_dict()  # type: ignore[assignment]
    if isinstance(m, Mapping):
        for k, v in m.items():
            row[k] = v
    # よくある別名の吸い上げ
    if "total_return" not in row and "return_total" in row:
        row["total_return"] = row["return_total"]
    return row


def aggregate_wfa_results(
    results: Sequence[Mapping[str, Any]],
) -> tuple[pd.DataFrame, Mapping[str, Any]]:
    """
    WFA等の結果リスト -> DataFrame（fold毎） + サマリdict を返す。
    - 各要素は run_wfa の戻り値要素（oos_start/oos_end/metrics/...）
    """
    if not results:
        return pd.DataFrame(), {}
    rows = [_flatten_metrics(r) for r in results]
    df = pd.DataFrame(rows)
    # 日付列をcoerce
    for c in ("oos_start", "oos_end"):
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], utc=True, errors="coerce")
    # サマリ（存在する数値列の平均等）
    num_cols = [
        c
        for c in df.columns
        if c not in ("oos_start", "oos_end") and pd.api.types.is_numeric_dtype(df[c])
    ]
    summary: dict[str, Any] = {}
    if num_cols:
        summary["mean"] = df[num_cols].mean(numeric_only=True).to_dict()
        summary["median"] = df[num_cols].median(numeric_only=True).to_dict()
    summary["folds"] = len(df)

    # --- 拡張: 複利合成 (foldごとの total_return を用いる単純版) -----------------------
    try:
        if "total_return" in df.columns and pd.api.types.is_numeric_dtype(df["total_return"]):
            rets = df["total_return"].dropna().astype(float)
            if len(rets) > 0:
                compounded = float((1.0 + rets).prod() - 1.0)
                summary["compounded"] = compounded
    except Exception:
        # 失敗しても既存の出力は維持
        pass

    # --- 拡張: 月次集計 (equity_curve から月次リターンを構築し fold間で平均) ---------
    def _monthly_returns_from_equity(eq: pd.Series) -> pd.Series:
        eq = eq.dropna().astype(float)
        if eq.empty:
            return pd.Series(dtype=float)
        # 月末の値を取り、前月末比のリターンを算出
        month_end = eq.resample("ME").last()
        mr = month_end.pct_change().dropna()
        mr.index = mr.index.strftime("%Y-%m")
        return mr

    try:
        monthly_buckets: dict[str, list[float]] = {}
        for r in results:
            eq = r.get("equity_curve")
            if isinstance(eq, pd.Series):
                mr = _monthly_returns_from_equity(eq)
                for m, v in mr.items():
                    monthly_buckets.setdefault(m, []).append(float(v))
        if monthly_buckets:
            by_month: dict[str, Any] = {}
            for m, arr in sorted(monthly_buckets.items()):
                s = pd.Series(arr, dtype=float)
                by_month[m] = {
                    "mean": float(s.mean()) if not s.empty else 0.0,
                    "median": float(s.median()) if not s.empty else 0.0,
                    "count": int(s.size),
                    "win_rate": float((s > 0).mean()) if not s.empty else 0.0,
                }
            summary["by_month"] = by_month
            # 追加: 最悪月（平均リターンの最小値）
            try:
                if by_month:
                    worst = min((v.get("mean", 0.0) for v in by_month.values()), default=0.0)
                    summary["worst_month"] = float(worst)
            except Exception:
                pass
    except Exception:
        # 集計拡張は任意。失敗しても既存の出力は維持
        pass

    # --- 拡張: OOS合計リターン分布の右尾/左尾を要約（上位5%/下位5%平均） ---------------
    try:
        if "total_return" in df.columns and pd.api.types.is_numeric_dtype(df["total_return"]):
            rets = df["total_return"].dropna().astype(float)
            if len(rets) >= MIN_TAIL_SAMPLES:  # 十分なサンプルがある場合のみ
                q_hi = float(rets.quantile(TAIL_Q_HI))
                q_lo = float(rets.quantile(TAIL_Q_LO))
                right_tail = float(rets[rets >= q_hi].mean()) if (rets >= q_hi).any() else 0.0
                left_tail = float(rets[rets <= q_lo].mean()) if (rets <= q_lo).any() else 0.0
                summary["right_tail"] = right_tail
                summary["left_tail"] = left_tail
    except Exception:
        pass
    return df, summary
