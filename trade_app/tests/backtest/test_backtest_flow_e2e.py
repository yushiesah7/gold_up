from types import SimpleNamespace

import pandas as pd
import pytz

from trade_app.apps.backtest.usecases import backtest_from_specs
from trade_app.apps.features.feature_calc import DefaultFeatureCalculator
from trade_app.apps.features.pipeline.plan_builder import DefaultPlanBuilder
from trade_app.domain.dto.ohlcv_frame import OhlcvFrameDTO
from trade_app.domain.ports.backtest import BacktestPort
from trade_app.domain.ports.data_feed import DataFeedPort
from trade_app.domain.ports.feature_calc import FeatureCalcPort
from trade_app.domain.ports.plan_builder import PlanBuilderPort


class FakeFeed(DataFeedPort):
    def load(
        self,
        symbols,
        start=None,
        end=None,
        columns=("open", "high", "low", "close", "volume"),
        timeframe=None,
        tz="UTC",
    ) -> OhlcvFrameDTO:
        idx = pd.date_range("2024-01-01", periods=120, freq="h", tz=pytz.UTC)
        df = pd.DataFrame(
            {
                "open": pd.Series(range(120), index=idx, dtype=float),
                "high": pd.Series(range(1, 121), index=idx, dtype=float),
                "low": pd.Series(range(120), index=idx, dtype=float) - 1,
                "close": pd.Series(range(120), index=idx, dtype=float),
                "volume": pd.Series(1, index=idx, dtype=float),
            },
            index=idx,
        )
        return OhlcvFrameDTO(frame=df, freq="h")


class FakeBacktester(BacktestPort):
    def run_from_signals(self, ohlcv, entries, exits, params=None):
        assert "open" in ohlcv.frame.columns
        return {"portfolio": SimpleNamespace(), "total_return": 0.0, "params": params or {}}

    def run_cv(self, *args, **kwargs):
        raise NotImplementedError


def test_backtest_flow_e2e():
    feed = FakeFeed()
    calc: FeatureCalcPort = DefaultFeatureCalculator()
    planner: PlanBuilderPort = DefaultPlanBuilder()
    bt: BacktestPort = FakeBacktester()

    feature_spec = {
        "rsi_14": {"kind": "rsi", "on": "close", "params": {"length": 14}},
        "sma_20": {"kind": "sma", "on": "close", "params": {"length": 20}},
    }
    plan_spec = {
        "entries": [{"op": "gt", "left": "rsi_14", "right": 50, "pre_shift": 1}],
        "exits": [{"op": "lt", "left": "rsi_14", "right": 50, "pre_shift": 1}],
    }

    res = backtest_from_specs(
        feed=feed,
        calc=calc,
        planner=planner,
        backtester=bt,
        feature_spec=feature_spec,
        plan_spec=plan_spec,
        symbols=["EURUSD"],
        tz="UTC",
        params={"fees": 0.001},
    )
    assert "portfolio" in res and "total_return" in res
    assert res["params"].get("fees") == 0.001
