from __future__ import annotations

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator


class OhlcvFrameDTO(BaseModel):
    """UTC awareなDatetimeIndexと必須列を契約として保持"""

    __responsibility__ = "OHLCV配列の受け渡し契約（UTC/TZ/列名）"

    # Pydantic v2: pandas.DataFrame を任意型として許可
    model_config = ConfigDict(arbitrary_types_allowed=True)
    frame: pd.DataFrame = Field(...)
    freq: str | None = Field(default=None)

    @field_validator("frame")
    @classmethod
    def _validate_frame(cls, v: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(v, pd.DataFrame):
            raise TypeError("frame must be pandas.DataFrame")
        if not isinstance(v.index, pd.DatetimeIndex):
            raise ValueError("index must be DatetimeIndex")
        if v.index.tz is None:
            raise ValueError("index must be timezone-aware (UTC expected)")
        # 列名を安全に小文字化
        lower_cols = [str(c).lower() for c in v.columns]
        req = {"open", "high", "low", "close"}
        if not req.issubset(set(lower_cols)):
            missing = req - set(lower_cols)
            raise ValueError(f"required columns missing: {missing}")
        v = v.copy()
        v.columns = lower_cols
        return v
