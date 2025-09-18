import pandas as pd
import pytz

from trade_app.apps.features.pipeline.run_to_signals import build_signals
from trade_app.domain.dto.pipeline_output import PipelineOutputDTO
from trade_app.domain.dto.plan_models import Clause, Plan


def test_build_signals_from_pipeline_output():
    idx = pd.date_range("2024-01-01", periods=60, freq="h", tz=pytz.UTC)
    df = pd.DataFrame(
        {
            "open": pd.Series(range(60), index=idx, dtype=float),
            "high": pd.Series(range(1, 61), index=idx, dtype=float),
            "low": pd.Series(range(60), index=idx, dtype=float) - 1,
            "close": pd.Series(range(60), index=idx, dtype=float),
            "volume": pd.Series(1, index=idx, dtype=float),
            "rsi_14": pd.Series([50] * 60, index=idx, dtype=float),
        },
        index=idx,
    )

    # features: ここでは rsi_14 だけを使う（src4のbundle済み想定）
    features = df[["rsi_14"]]

    plan = Plan(entries=[Clause(op="gt", left="rsi_14", right=49, pre_shift=1)])
    out = PipelineOutputDTO(features=features, plan=plan)

    sig = build_signals(out)
    assert sig.entries.any()
    assert not sig.exits.any()
