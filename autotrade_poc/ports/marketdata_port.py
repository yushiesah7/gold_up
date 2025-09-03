from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from autotrade_poc.domain.models.market import Symbol, Timeframe
from autotrade_poc.domain.models.order import Bar


class MarketDataPort(ABC):
    @abstractmethod
    def latest_bar(self, symbol: Symbol, timeframe: Timeframe) -> Bar:
        raise NotImplementedError

    @abstractmethod
    def stream_bars(self, symbol: Symbol, timeframe: Timeframe) -> Iterable[Bar]:
        """新バーをプッシュ/ポーリングで受け取るジェネレータ。"""
        raise NotImplementedError
