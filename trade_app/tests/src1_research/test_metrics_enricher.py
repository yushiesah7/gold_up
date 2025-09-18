import pandas as pd
import pytz

from trade_app.apps.research.metrics.enricher import enrich_result


def test_enrich_result_adds_mdd_cagr_sharpe():
    idx = pd.date_range("2024-01-01", periods=100, freq="h", tz=pytz.UTC)
    # 単調増加のエクイティ（Sharpe>0、CAGR>0、MDD=0 付近）
    base = 100.0
    inc = pd.Series(range(100), index=idx, dtype=float) * 0.01
    eq = (base + inc).rename("equity")

    res = {"equity_curve": eq, "metrics": {"total_return": 0.1}}

    out = enrich_result(res, rf=0.0)
    m = out["metrics"]
    assert "max_drawdown" in m and m["max_drawdown"] <= 0.0 + 1e-9
    assert "cagr" in m and m["cagr"] >= 0.0
    assert "sharpe_ratio" in m
