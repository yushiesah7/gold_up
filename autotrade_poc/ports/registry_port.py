from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from autotrade_poc.domain.models.spec import LiveSpec


class RegistryPort(ABC):
    @abstractmethod
    def load_live_specs(self) -> Sequence[LiveSpec]:
        """YAML群を読み込み、厳密型 LiveSpec にマッピングして返す。"""
        raise NotImplementedError
