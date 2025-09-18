from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytz

from trade_app.adapters.results.lock_sink_file import FileLockSinkAdapter
from trade_app.apps.features.feature_calc import DefaultFeatureCalculator
from trade_app.apps.features.pipeline.plan_builder import DefaultPlanBuilder
from trade_app.apps.research.explorer.run_explorer import run_explorer
from trade_app.apps.research.splitters.walkforward import WalkForwardSplitter
from trade_app.domain.dto.ohlcv_frame import OhlcvFrameDTO
from trade_app.domain.ports.backtest import BacktestPort
from trade_app.domain.ports.data_feed import DataFeedPort
from trade_app.domain.ports.optimizer import ObjectiveFn, OptimizerPort
from trade_app.domain.ports.sampler import SamplerPort, Space


# ---- Fakes ----
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
        idx = pd.date_range("2024-01-01", periods=80, freq="h", tz=pytz.UTC)
        df = pd.DataFrame(
            {
                "open": pd.Series(range(80), index=idx, dtype=float),
                "high": pd.Series(range(1, 81), index=idx, dtype=float),
                "low": pd.Series(range(80), index=idx, dtype=float) - 1,
                "close": pd.Series(range(80), index=idx, dtype=float),
                "volume": pd.Series(1, index=idx, dtype=float),
            },
            index=idx,
        )
        return OhlcvFrameDTO(frame=df, freq="h")


class FakeBacktester(BacktestPort):
    def run_from_signals(self, ohlcv, entries, exits, params=None):
        # 単純な“良さ”: entries の True が多いほど Sharpe高い と仮定
        sharpe = float(entries.sum()) / max(len(entries), 1)
        # equityは線形（雰囲気だけ）
        eq = pd.Series(range(len(ohlcv.frame)), index=ohlcv.frame.index, dtype=float)
        pf = SimpleNamespace(equity=eq)
        return {"portfolio": pf, "metrics": {"total_return": sharpe}}

    def run_cv(self, *args, **kwargs):
        raise NotImplementedError


class FakeSampler(SamplerPort):
    def __init__(self, points):
        self.points = points

    def sample(self, space: Space, n: int, *, seed: int | None = None):
        return self.points[:n]


class FakeOptimizer(OptimizerPort):
    def __init__(self):
        self.calls = []

    def optimize(
        self,
        objective: ObjectiveFn,
        space: Space,
        *,
        n_trials: int,
        timeout_sec=None,
        seed=None,
        initial_points=None,
    ):
        best_params, best_score = None, float("-inf")
        trials = []
        # 初期点 + 少数の乱択（ここでは初期点だけで十分）
        for p in initial_points or []:
            v = objective(p)
            trials.append({"params": p, "value": v})
            if v > best_score:
                best_score, best_params = v, p
        return best_params or {}, float(best_score), trials


def test_run_explorer_loop_writes_lock(tmp_path: Path):
    feed = FakeFeed()
    calc = DefaultFeatureCalculator()
    planner = DefaultPlanBuilder()
    splitter = WalkForwardSplitter(train_size=40, test_size=20)
    backtester = FakeBacktester()

    features_spec = {
        "rsi_{{rsi.length}}": {
            "kind": "rsi",
            "on": "close",
            "params": {"length": "{{rsi.length}}"},
        },
        "sma_{{sma.len}}": {"kind": "sma", "on": "close", "params": {"length": "{{sma.len}}"}},
    }
    plan_spec = {
        "entries": [{"op": "gt", "left": "rsi_{{rsi.length}}", "right": 50, "pre_shift": 1}],
        "exits": [{"op": "lt", "left": "rsi_{{rsi.length}}", "right": 50, "pre_shift": 1}],
    }
    space = {
        "rsi.length": {"type": "int", "low": 5, "high": 20, "step": 1},
        "sma.len": {"type": "int", "low": 5, "high": 30, "step": 5},
    }

    # 初期点2つ（“rsi.lengthが大きいほど entries 多い”よう誘導する仮定）
    sampler = FakeSampler(
        points=[{"rsi.length": 18, "sma.len": 10}, {"rsi.length": 6, "sma.len": 30}]
    )
    optimizer = FakeOptimizer()
    lock_sink = FileLockSinkAdapter()

    out = run_explorer(
        feed=feed,
        calc=calc,
        planner=planner,
        backtester=backtester,
        splitter=splitter,
        features_spec=features_spec,
        plan_spec=plan_spec,
        space=space,
        symbols=["EURUSD"],
        full_start=pd.Timestamp("2024-01-01", tz=pytz.UTC),
        full_end=pd.Timestamp("2024-01-04 07:00", tz=pytz.UTC),
        timeframe="h",
        tz="UTC",
        sampler=sampler,
        optimizer=optimizer,
        lock_sink=lock_sink,
        out_dir=tmp_path,
        n_init=2,
        n_trials=2,
        seed=7,
    )

    assert "best_params" in out and out["best_params"]["rsi.length"] in (18, 6)
    assert out["lock_path"].exists()
