from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import pandas as pd


def _infer_annualization(index: pd.DatetimeIndex) -> float:
    """Indexから年換算倍率を推定（近似）。"""
    if len(index) < 2:  # noqa: PLR2004
        return 252.0  # デフォ：日次
    dt = (index[1] - index[0]).to_pytimedelta().total_seconds()
    # 粗い判定：h/min/d の3段
    if dt <= 60.0:  # 1分足近辺  # noqa: PLR2004
        return 252.0 * 24.0 * 60.0
    if dt <= 3600.0:  # 1時間足近辺  # noqa: PLR2004
        return 252.0 * 24.0
    if dt <= 86400.0:  # 日足近辺  # noqa: PLR2004
        return 252.0
    return 52.0  # 週足近辺（簡易）


def _drawdown(equity: pd.Series) -> tuple[pd.Series, float]:
    """エクイティカーブからDD系列とMDD(%)を返す。"""
    eq = equity.astype(float)
    peak = eq.cummax()
    dd = (eq / peak - 1.0).fillna(0.0)
    mdd = float(dd.min()) if len(dd) > 0 else 0.0
    return dd, mdd


def _cagr(equity: pd.Series) -> float:
    if len(equity) < 2:  # noqa: PLR2004
        return 0.0
    start, end = float(equity.iloc[0]), float(equity.iloc[-1])
    if start <= 0.0 or end <= 0.0:
        return 0.0
    delta = equity.index[-1] - equity.index[0]
    # 年換算を秒ベースで近似（極端に短い期間の不安定化を避ける）
    seconds = getattr(delta, "total_seconds", lambda: 0.0)()  # type: ignore[misc]
    years = seconds / (365.25 * 86400.0)
    if years <= 0.0:
        return 0.0
    # 1ヶ月未満など極端に短い期間は指数計算が不安定になり得るため0を返す
    if years < (1.0 / 12.0):  # ~1ヶ月未満
        return 0.0
    return (end / start) ** (1.0 / years) - 1.0


def _sharpe(returns: pd.Series, annualization: float, rf: float = 0.0) -> float:
    r = returns.astype(float) - (rf / annualization)
    mu = float(r.mean())
    sd = float(r.std(ddof=0))
    if sd == 0.0:
        return 0.0
    return mu / sd * math.sqrt(annualization)


def enrich_result(result: Mapping[str, Any], *, rf: float = 0.0) -> dict[str, Any]:
    """
    Backtest結果の dict を受け取り、欠けているメトリクスを補完して返す。
    - equity_curve or portfolio.equity があればDD/CAGR/Sharpeを計算して埋める
    - 既に存在するキーは上書きしない
    """
    out = dict(result)
    metrics = dict(out.get("metrics", {}))

    # Equity の取り出し
    eq = None
    if isinstance(out.get("equity_curve"), pd.Series):
        eq = out["equity_curve"]
    elif "portfolio" in out and hasattr(out["portfolio"], "equity"):
        eq = out["portfolio"].equity

    if isinstance(eq, pd.Series) and isinstance(eq.index, pd.DatetimeIndex):
        ann = _infer_annualization(eq.index)
        rets = eq.pct_change().fillna(0.0)
        _, mdd = _drawdown(eq)
        cagr = _cagr(eq)
        shp = _sharpe(rets, annualization=ann, rf=rf)
        metrics.setdefault("max_drawdown", mdd)
        metrics.setdefault("cagr", cagr)
        metrics.setdefault("sharpe_ratio", shp)

    # 既にトップレベルにある代表的なメトリクスを metrics に折りたたむ
    for k in ("total_return", "sharpe_ratio", "trades"):
        if k in out and k not in metrics:
            metrics[k] = out[k]

    out["metrics"] = metrics
    return out
