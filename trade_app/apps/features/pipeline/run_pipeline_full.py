from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, ClassVar

from trade_app.apps.features.indicators.session import session_feature
from trade_app.apps.features.pipeline.loader import load_ohlcv
from trade_app.domain.dto.pipeline_full_output import PipelineFullOutputDTO
from trade_app.domain.ports.data_feed import DataFeedPort
from trade_app.domain.ports.feature_calc import FeatureCalcPort
from trade_app.domain.ports.plan_builder import PlanBuilderPort
from trade_app.utils.timing import build_logger, time_phase

__responsibility__: ClassVar[str] = "OHLCV→features→plan をまとめて返す（OHLCV込み）"


def run_pipeline_full(
    *,
    feed: DataFeedPort,
    calc: FeatureCalcPort,
    planner: PlanBuilderPort,
    feature_spec: Mapping[str, Mapping[str, Any]],
    plan_spec: Mapping[str, Any],
    symbols: Iterable[str],
    start: str | None = None,
    end: str | None = None,
    columns: Sequence[str] = ("open", "high", "low", "close", "volume"),
    timeframe: str | None = None,
    tz: str = "UTC",
    run_params: Mapping[str, Any] | None = None,
) -> PipelineFullOutputDTO:
    log = build_logger()
    with time_phase(
        log,
        "load_ohlcv",
        symbol=",".join(list(symbols)),
        timeframe=str(timeframe or ""),
        session="",
    ):
        ohlcv = load_ohlcv(
            feed,
            symbols,
            start=start,
            end=end,
            columns=columns,
            timeframe=timeframe,
            tz=tz,
        )
    with time_phase(
        log,
        "calc_features",
        symbol=",".join(list(symbols)),
        timeframe=str(timeframe or ""),
        session="",
    ):
        bundle = calc.compute(ohlcv, feature_spec)
    # Inject session_active if session_preset/windows is provided via run_params
    features_df = bundle.features.copy()
    sess = (run_params or {}).get("session_preset") if run_params else None
    if isinstance(sess, dict):
        # Accept preset name or explicit window dict
        windows: list[Mapping[str, Any]]
        if sess.get("type") in {"all", "window"}:
            windows = [sess]
        else:
            # If only name provided, fall back to preset lookup inside session_feature via preset
            windows = []
        try:
            if windows:
                mask = session_feature(features_df, windows=windows)
            else:
                mask = session_feature(features_df, preset=sess.get("name"), tz=sess.get("tz", tz))
            features_df["session_active"] = mask.reindex(features_df.index)
        except Exception:
            # セッション機能は任意。失敗時もパイプラインは継続
            # （features不足なら後段で0スコアに収束）
            pass
    plan = planner.build(plan_spec)
    return PipelineFullOutputDTO(ohlcv=ohlcv, features=features_df, plan=plan)
