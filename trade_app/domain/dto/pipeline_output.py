from __future__ import annotations

from typing import ClassVar

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from trade_app.domain.dto.plan_models import Plan


class PipelineOutputDTO(BaseModel):
    """src4パイプラインの出力（features + plan）。純関数へはここから取り出して渡す。"""

    __responsibility__: ClassVar[str] = "変換結果の受け渡しDTO（featuresとplanの組）"
    model_config = ConfigDict(arbitrary_types_allowed=True)

    features: pd.DataFrame = Field(...)
    plan: Plan = Field(...)
