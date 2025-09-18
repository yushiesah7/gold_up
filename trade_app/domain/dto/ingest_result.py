from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class IngestResultDTO(BaseModel):
    """1シンボル分の結果サマリ"""

    __responsibility__: ClassVar[str] = "Ingest結果（件数/パス等）"
    model_config = ConfigDict(arbitrary_types_allowed=True)

    symbol: str = Field(...)
    timeframe: str = Field(...)
    rows: int = Field(...)
    path: Path = Field(...)
