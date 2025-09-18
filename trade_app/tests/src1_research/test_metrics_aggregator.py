import pandas as pd
import pytz

from trade_app.apps.research.metrics.aggregator import aggregate_wfa_results


def test_aggregate_wfa_results_builds_table_and_summary():
    idx = pd.date_range("2024-01-01", periods=48, freq="h", tz=pytz.UTC)
    results = [
        {
            "oos_start": idx[0],
            "oos_end": idx[11],
            "metrics": {"total_return": 0.10, "sharpe_ratio": 1.2},
        },
        {
            "oos_start": idx[12],
            "oos_end": idx[23],
            "metrics": {"total_return": 0.05, "sharpe_ratio": 0.8},
        },
        {
            "oos_start": idx[24],
            "oos_end": idx[35],
            "metrics": {"total_return": -0.02, "sharpe_ratio": 0.4},
        },
    ]
    df, summary = aggregate_wfa_results(results)
    assert len(df) == 3
    assert "total_return" in df.columns
    assert summary["folds"] == 3
    assert "mean" in summary and "total_return" in summary["mean"]
    # 追加: worst_month/right_tail/left_tail が summary に存在するか（存在すれば型は数値）
    if "worst_month" in summary:
        assert isinstance(summary["worst_month"], float)
    if "right_tail" in summary:
        assert isinstance(summary["right_tail"], float)
    if "left_tail" in summary:
        assert isinstance(summary["left_tail"], float)
