from __future__ import annotations

from typing import ClassVar

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SignalsDTO(BaseModel):
    """純関数decideの出力（entries/short_entries/exits の同Index bool Series）"""

    __responsibility__: ClassVar[str] = "戦略シグナルの受け渡しDTO"
    model_config = ConfigDict(arbitrary_types_allowed=True)

    entries: pd.Series = Field(...)
    short_entries: pd.Series = Field(...)
    exits: pd.Series = Field(...)

    @staticmethod
    def _validate_series(s: pd.Series) -> pd.Series:
        if not isinstance(s, pd.Series):
            raise TypeError("signal must be pandas.Series")
        if not isinstance(s.index, pd.DatetimeIndex):
            raise ValueError("signal.index must be DatetimeIndex")
        if s.index.tz is None:
            raise ValueError("signal.index must be timezone-aware")
        # bool化（NaNはFalseへ）
        s = s.fillna(False).astype(bool)
        return s

    @field_validator("entries")
    @classmethod
    def _v_entries(cls, v: pd.Series) -> pd.Series:
        return cls._validate_series(v)

    @field_validator("short_entries")
    @classmethod
    def _v_short_entries(cls, v: pd.Series) -> pd.Series:
        return cls._validate_series(v)

    @field_validator("exits")
    @classmethod
    def _v_exits(cls, v: pd.Series) -> pd.Series:
        return cls._validate_series(v)
