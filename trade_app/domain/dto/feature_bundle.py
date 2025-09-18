from __future__ import annotations

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator


class FeatureBundleDTO(BaseModel):
    """features: 同一IndexのDataFrame（NaNはbundle時点で解消済みが契約）"""

    __responsibility__ = "features束ねの契約"

    model_config = ConfigDict(arbitrary_types_allowed=True)
    features: pd.DataFrame = Field(...)

    @field_validator("features")
    @classmethod
    def _validate_features(cls, df: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("features.index must be DatetimeIndex")
        if df.index.tz is None:
            raise ValueError("features.index must be timezone-aware")
        if df.isna().any().any():
            raise ValueError("features contain NaN; bundle前処理で解消してください")
        return df
