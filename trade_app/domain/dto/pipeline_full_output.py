from __future__ import annotations

from typing import ClassVar

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from trade_app.domain.dto.ohlcv_frame import OhlcvFrameDTO
from trade_app.domain.dto.plan_models import Plan


class PipelineFullOutputDTO(BaseModel):
    """OHLCV + features + plan（純関数・検証へ橋渡しに使う）"""

    __responsibility__: ClassVar[str] = "変換結果のフルDTO（OHLCV/Features/Plan）"
    model_config = ConfigDict(arbitrary_types_allowed=True)

    ohlcv: OhlcvFrameDTO = Field(...)
    features: pd.DataFrame = Field(...)
    plan: Plan = Field(...)
