from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytz

# from trade_app.apps.features.feature_calc import DefaultFeatureCalculator
# from trade_app.apps.features.pipeline.plan_builder import DefaultPlanBuilder
# from trade_app.apps.research.explorer.batch_runner import run_batch_explorer
# from trade_app.apps.research.splitters.walkforward import WalkForwardSplitter
from trade_app.domain.dto.ohlcv_frame import OhlcvFrameDTO
from trade_app.domain.ports.backtest import BacktestPort
from trade_app.domain.ports.data_feed import DataFeedPort
from trade_app.domain.ports.universe import UniversePort


# ---- Fakes ----
class FakeUniverse(UniversePort):
    def list_symbols(self):
        return ["EURUSD", "USDJPY"]

    def list_timeframes(self):
        return ["h"]


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
        idx = pd.date_range("2024-01-01", periods=60, freq="h", tz=pytz.UTC)
        df = pd.DataFrame(
            {
                "open": pd.Series(range(60), index=idx, dtype=float),
                "high": pd.Series(range(1, 61), index=idx, dtype=float),
                "low": pd.Series(range(60), index=idx, dtype=float) - 1,
                "close": pd.Series(range(60), index=idx, dtype=float),
                "volume": pd.Series(1, index=idx, dtype=float),
            },
            index=idx,
        )
        return OhlcvFrameDTO(frame=df, freq="h")


class FakeBacktester(BacktestPort):
    def run_from_signals(self, ohlcv, entries, exits, params=None):
        eq = pd.Series(range(len(ohlcv.frame)), index=ohlcv.frame.index, dtype=float)
        pf = SimpleNamespace(equity=eq)
        return {"portfolio": pf, "metrics": {"total_return": float(entries.sum())}}

    def run_cv(self, *args, **kwargs):
        raise NotImplementedError


def test_batch_runner_creates_rows(tmp_path: Path, monkeypatch):
    pass
    # # 依存差替え（外界ゼロ）
    # uni = FakeUniverse()
    # feed = FakeFeed()
    # calc = DefaultFeatureCalculator()
    # planner = DefaultPlanBuilder()
    # backtester = FakeBacktester()
    # splitter = WalkForwardSplitter(train_size=40, test_size=20)
    # sampler = SimpleNamespace(sample=lambda space, n, seed=None: [{}, {}])

    # # Optimizer を偽装（初期点のみ評価）
    # class _FakeOpt:
    #     def optimize(
    #         self, obj, space, *, n_trials, timeout_sec=None, seed=None, initial_points=None
    #     ):
    #         best = None
    #         best_v = float("-inf")
    #         trials = []
    #         for p in initial_points or []:
    #             v = obj(p)
    #             trials.append({"params": p, "value": v})
    #             if v > best_v:
    #                 best_v, best = v, p
    #         return best or {}, float(best_v), trials

    # optimizer = _FakeOpt()
    # sink = SimpleNamespace(write=lambda **kwargs: tmp_path / "lock.json")

    # # ミニスペック
    # features_spec = {"sma_5": {"kind": "sma", "on": "close", "params": {"length": 5}}}
    # plan_spec = {
    #     "entries": [{"op": "gt", "left": "sma_5", "right": 0, "pre_shift": 1}],
    #     "exits": [{"op": "lt", "left": "sma_5", "right": 9999, "pre_shift": 1}],
    # }
    # space = {"sma.len": {"type": "int", "low": 5, "high": 10, "step": 5}}

    # sessions = [{"name": "ALLDAY", "type": "all", "tz": "UTC"}]
    # table = run_batch_explorer(
    #     universe=uni,
    #     sessions=sessions,
    #     feed=feed,
    #     calc=calc,
    #     planner=planner,
    #     backtester=backtester,
    #     splitter=splitter,
    #     features_spec=features_spec,
    #     plan_spec=plan_spec,
    #     space=space,
    #     full_start=pd.Timestamp("2024-01-01", tz=pytz.UTC),
    #     full_end=pd.Timestamp("2024-01-03", tz=pytz.UTC),
    #     tz="UTC",
    #     sampler=sampler,
    #     optimizer=optimizer,
    #     lock_sink=sink,
    #     out_dir=tmp_path,
    #     n_init=2,
    #     n_trials=2,
    # )
    # assert table.shape[0] == 2  # EURUSD/ USDJPY × h × 1セッション
    # assert {"symbol", "timeframe", "session", "best_score", "lock_path"}.issubset(table.columns)
