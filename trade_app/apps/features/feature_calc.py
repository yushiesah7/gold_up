from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import pandas as pd

from trade_app.apps.features.indicators.atr import atr
from trade_app.apps.features.indicators.bb import bb
from trade_app.apps.features.indicators.donchian import donchian
from trade_app.apps.features.indicators.keltner import keltner
from trade_app.apps.features.indicators.ma import ema, sma
from trade_app.apps.features.indicators.macd import macd
from trade_app.apps.features.indicators.roc import roc
from trade_app.apps.features.indicators.rsi import rsi
from trade_app.apps.features.indicators.session import session_feature as session
from trade_app.apps.features.indicators.stoch import stoch
from trade_app.apps.features.indicators.vwap import vwap
from trade_app.apps.features.indicators.zscore import zscore
from trade_app.apps.features.pipeline.feature_bundler import bundle_features
from trade_app.domain.dto.feature_bundle import FeatureBundleDTO
from trade_app.domain.dto.ohlcv_frame import OhlcvFrameDTO
from trade_app.domain.ports.feature_calc import FeatureCalcPort

IndicatorFn = Callable[..., pd.Series]  # 単一出力
MultiIndicatorFn = Callable[..., dict[str, pd.Series]]  # 複数出力

DEFAULT_REGISTRY: dict[str, Callable[..., Any]] = {
    # 単一出力
    "rsi": rsi,
    "sma": sma,
    "ema": ema,
    # 原始列をそのまま返す（on: "close" など）。検証・組み合わせ用途のための最小I/F。
    "identity": lambda s, **_: s,
    "atr": atr,
    "roc": roc,
    "zscore": zscore,
    "vwap": vwap,
    "session": session,
    # 複数出力
    "bb": bb,
    "macd": macd,
    "stoch": stoch,
    "donchian": donchian,
    "keltner": keltner,
}


class DefaultFeatureCalculator(FeatureCalcPort):
    """
    spec 形式例:
      "bb_20_2": {"kind":"bb", "on":"close", "params":{"window":20,"mult":2}}
      "macd": {"kind":"macd", "on":"close", "params":{"fast":12,"slow":26,"signal":9}}
      "stoch": {"kind":"stoch", "on":["high","low","close"], "params":{"k":14,"d":3,"smooth":1}}
      "vwap": {"kind":"vwap", "on":{"price":"close","volume":"volume"}, "params":{"window":30}}
    出力名は spec のキーを接頭辞に、マルチ出力は `${prefix}_${key}` を付ける。
    """

    __responsibility__ = "features spec を解釈して各インジを決定的に計算（マルチ出力対応）"

    def __init__(self, registry: Mapping[str, Callable[..., Any]] | None = None) -> None:
        self._reg: dict[str, Callable[..., Any]] = dict(registry or DEFAULT_REGISTRY)

    def compute(
        self,
        ohlcv: OhlcvFrameDTO,
        spec: Mapping[str, Mapping[str, Any]],
    ) -> FeatureBundleDTO:
        frame = ohlcv.frame
        produced: dict[str, pd.Series] = {}

        for prefix, cfg in spec.items():
            kind = str(cfg.get("kind", "")).lower()
            fn = self._reg.get(kind)
            if fn is None:
                raise ValueError(f"unknown indicator kind: {kind}")
            params = dict(cfg.get("params", {}))
            on = cfg.get("on", "close")

            def get_series(name: str) -> pd.Series:
                return frame[str(name)]

            out_obj: Any
            if kind in {"rsi", "sma", "ema", "zscore", "roc", "identity"}:
                series = get_series(on if isinstance(on, str) else "close")
                out_obj = fn(series, **params)
            elif kind == "atr":
                cols = on if isinstance(on, list | tuple) else ["high", "low", "close"]
                out_obj = fn(frame[cols[0]], frame[cols[1]], frame[cols[2]], **params)
            elif kind in {"bb", "macd"}:
                series = get_series(on if isinstance(on, str) else "close")
                out_obj = fn(series, **params)
            elif kind == "session":
                # session feature は DataFrame（index）から生成
                out_obj = fn(frame, **params)
            elif kind == "stoch":
                cols = on if isinstance(on, list | tuple) else ["high", "low", "close"]
                out_obj = fn(frame[cols[0]], frame[cols[1]], frame[cols[2]], **params)
            elif kind == "donchian":
                cols = on if isinstance(on, list | tuple) else ["high", "low"]
                out_obj = fn(frame[cols[0]], frame[cols[1]], **params)
            elif kind == "keltner":
                cols = on if isinstance(on, list | tuple) else ["high", "low", "close"]
                out_obj = fn(frame[cols[0]], frame[cols[1]], frame[cols[2]], **params)
            elif kind == "vwap":
                if isinstance(on, dict):
                    price = get_series(on.get("price", "close"))
                    volume = get_series(on.get("volume", "volume"))
                else:
                    cols = on if isinstance(on, list | tuple) else ["close", "volume"]
                    price, volume = frame[cols[0]], frame[cols[1]]
                out_obj = fn(price, volume, **params)
            else:
                raise ValueError(f"unhandled indicator kind: {kind}")

            if isinstance(out_obj, pd.Series):
                produced[prefix] = out_obj
            elif isinstance(out_obj, dict):
                for k, series in out_obj.items():
                    produced[f"{prefix}_{k}"] = series
            else:
                raise TypeError(f"indicator '{kind}' returned unsupported type: {type(out_obj)}")

        return bundle_features(ohlcv, produced, nan_policy="drop_head")
