from __future__ import annotations

from typing import ClassVar

from trade_app.domain.dto.pipeline_output import PipelineOutputDTO
from trade_app.domain.dto.signals import SignalsDTO
from trade_app.domain.services.decider import decide

__responsibility__: ClassVar[str] = (
    "src4出力（features+plan）を純関数decideに渡してSignalsDTOを返す"
)


def build_signals(pipeline_out: PipelineOutputDTO) -> SignalsDTO:
    """features + plan → decide → signals"""
    return decide(pipeline_out.features, pipeline_out.plan)
