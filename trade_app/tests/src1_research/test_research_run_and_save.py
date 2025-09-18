from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytz

from trade_app.adapters.results.file_results_sink import FileResultsSinkAdapter
from trade_app.apps.features.feature_calc import DefaultFeatureCalculator
from trade_app.apps.features.pipeline.plan_builder import DefaultPlanBuilder
from trade_app.apps.research.orchestrator_save import run_wfa_and_save
from trade_app.apps.research.splitters.walkforward import WalkForwardSplitter
from trade_app.domain.dto.ohlcv_frame import OhlcvFrameDTO
from trade_app.domain.ports.backtest import BacktestPort
from trade_app.domain.ports.data_feed import DataFeedPort


class FakeFeed(DataFeedPort):
    def load(
        self,
        symbols,
        start=None,
        end=None,
        columns=("open", "high", "low", "close", "volume"),
        timeframe=None,
        tz="UTC",
    ):
        idx = pd.date_range("2024-01-01", periods=100, freq="h", tz=pytz.UTC)
        df = pd.DataFrame(
            {
                "open": pd.Series(range(100), index=idx, dtype=float),
                "high": pd.Series(range(1, 101), index=idx, dtype=float),
                "low": pd.Series(range(100), index=idx, dtype=float) - 1,
                "close": pd.Series(range(100), index=idx, dtype=float),
                "volume": pd.Series(1, index=idx, dtype=float),
            },
            index=idx,
        )
        return OhlcvFrameDTO(frame=df, freq="h")


class FakeBacktester(BacktestPort):
    def run_from_signals(self, ohlcv, entries, exits, params=None):
        eq = pd.Series(range(len(ohlcv.frame)), index=ohlcv.frame.index, dtype=float)
        pf = SimpleNamespace(equity=eq)
        return {"portfolio": pf, "metrics": {"total_return": 0.1}}

    def run_cv(self, *args, **kwargs):
        raise NotImplementedError


def test_run_wfa_and_save(tmp_path: Path):
    feed = FakeFeed()
    calc = DefaultFeatureCalculator()
    planner = DefaultPlanBuilder()
    bt = FakeBacktester()
    splitter = WalkForwardSplitter(train_size=60, test_size=20)
    sink = FileResultsSinkAdapter()

    feature_spec = {"sma_5": {"kind": "sma", "on": "close", "params": {"length": 5}}}
    plan_spec = {
        "entries": [{"op": "gt", "left": "sma_5", "right": 0, "pre_shift": 1}],
        "exits": [{"op": "lt", "left": "sma_5", "right": 9999, "pre_shift": 1}],
    }

    out = run_wfa_and_save(
        feed=feed,
        calc=calc,
        planner=planner,
        backtester=bt,
        splitter=splitter,
        feature_spec=feature_spec,
        plan_spec=plan_spec,
        symbols=["EURUSD"],
        full_start=pd.Timestamp("2024-01-01", tz=pytz.UTC),
        full_end=pd.Timestamp("2024-01-05 03:00", tz=pytz.UTC),
        sink=sink,
        base_dir=tmp_path,
        experiment_name="exp1",
        fmt="parquet",
    )

    assert out.get("paths")
    assert out["paths"].get("folds_parquet", None) and out["paths"]["folds_parquet"].exists()
    assert out["paths"]["summary_json"].exists()
    assert out["table"].shape[0] >= 1
