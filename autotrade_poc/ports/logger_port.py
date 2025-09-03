from __future__ import annotations

from abc import ABC, abstractmethod


class LoggerPort(ABC):
    @abstractmethod
    def info(self, msg: str) -> None:  # 最小の会話語彙
        raise NotImplementedError

    @abstractmethod
    def error(self, msg: str) -> None:
        raise NotImplementedError
