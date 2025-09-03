from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class ClockPort(ABC):
    @abstractmethod
    def now(self) -> datetime:  # タイムゾーンはアダプタ側で扱う
        raise NotImplementedError

    @abstractmethod
    def sleep_until(self, dt: datetime) -> None:
        raise NotImplementedError
