import pandas as pd
import pytz

from trade_app.domain.dto.plan_models import Clause, Plan
from trade_app.domain.services.decider import decide


def _df():
    idx = pd.date_range("2024-01-01", periods=6, freq="h", tz=pytz.UTC)
    return pd.DataFrame(
        {
            "a": pd.Series([1, 2, 3, 4, 5, 6], index=idx, dtype=float),
            "b": pd.Series([3, 3, 3, 3, 3, 3], index=idx, dtype=float),
        },
        index=idx,
    )


def test_gt_between_cross_with_preshift():
    df = _df()

    plan = Plan(
        entries=[
            Clause(op="gt", left="a", right=1, pre_shift=1),
            Clause(op="between", left="b", right=[2.5, 3.5], pre_shift=1),
        ],
        short_entries=[Clause(op="cross_under", left="a", right="b", pre_shift=1)],
        exits=[Clause(op="cross_over", left="a", right="b", pre_shift=1)],
    )
    sig = decide(df, plan)

    # シンプル検証：index整合と型
    assert sig.entries.index.equals(df.index)
    assert sig.entries.dtype == bool
    assert sig.exits.dtype == bool
    # cross の存在チェック（a と b は3で交差）
    assert sig.exits.any() or sig.short_entries.any()
