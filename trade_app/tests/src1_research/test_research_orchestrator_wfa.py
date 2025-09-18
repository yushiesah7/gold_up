from types import SimpleNamespace

import pandas as pd
import pytz

from trade_app.apps.features.feature_calc import DefaultFeatureCalculator
from trade_app.apps.features.pipeline.plan_builder import DefaultPlanBuilder
from trade_app.apps.research.orchestrator import run_single_backtest, run_wfa
from trade_app.apps.research.splitters.walkforward import WalkForwardSplitter
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
        # 100本固定のOHLCV
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
        # 期間のバー数を metrics に含める（簡易検証用）
        return {"portfolio": SimpleNamespace(), "metrics": {"bars": len(ohlcv.frame)}}

    def run_cv(self, *args, **kwargs):
        raise NotImplementedError


def test_run_single_and_wfa():
    feed = FakeFeed()
    calc: FeatureCalcPort = DefaultFeatureCalculator()
    planner: PlanBuilderPort = DefaultPlanBuilder()
    bt: BacktestPort = FakeBacktester()

    feature_spec = {"sma_5": {"kind": "sma", "on": "close", "params": {"length": 5}}}
    plan_spec = {
        "entries": [{"op": "gt", "left": "sma_5", "right": 0, "pre_shift": 1}],
        "exits": [{"op": "lt", "left": "sma_5", "right": 9999, "pre_shift": 1}],
    }

    # 単発
    res1 = run_single_backtest(
        feed=feed,
        calc=calc,
        planner=planner,
        backtester=bt,
        feature_spec=feature_spec,
        plan_spec=plan_spec,
        symbols=["EURUSD"],
        timeframe="h",
        tz="UTC",
    )
    assert "metrics" in res1 and res1["metrics"]["bars"] == 100

    # WFA: train=60, test=20 → 少なくとも2区間
    splitter = WalkForwardSplitter(train_size=60, test_size=20)
    res_list = run_wfa(
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
        timeframe="h",
        tz="UTC",
    )
    assert len(res_list) >= 2
    assert all("metrics" in r for r in res_list)
