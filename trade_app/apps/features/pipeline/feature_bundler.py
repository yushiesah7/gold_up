from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from trade_app.domain.dto.feature_bundle import FeatureBundleDTO
from trade_app.domain.dto.ohlcv_frame import OhlcvFrameDTO


def bundle_features(
    ohlcv: OhlcvFrameDTO,
    feats: Mapping[str, pd.Series],
    nan_policy: str = "drop_head",  # "drop_all" 等に拡張可
) -> FeatureBundleDTO:
    """
    features を同Indexに束ね、NaNを前処理で解消（純関数にはNaNを入れない契約）
    - ループ変数の上書きを避けてRuff PLW2901を解消
    - 列名は受け取った辞書キーを優先（Series.nameは無視）
    """
    df = pd.DataFrame(index=ohlcv.frame.index)
    for name, series in feats.items():
        aligned = series.reindex(df.index)
        df[name] = aligned

    if nan_policy == "drop_head":
        # 各列の先頭有効位置の最大を採用し、まとめて先頭NaNを落とす
        first_valid_per_col = df.apply(pd.Series.first_valid_index)
        first_valid = first_valid_per_col.max()
        if first_valid is not None:
            df = df.loc[first_valid:]
    elif nan_policy == "drop_all":
        df = df.dropna()
    else:
        raise ValueError(f"unknown nan_policy: {nan_policy}")

    if df.isna().any().any():
        # 先頭以外に残存NaNがある場合は契約違反として落とす
        raise ValueError("features contain NaN after bundling")

    return FeatureBundleDTO(features=df)
