from __future__ import annotations

from abc import ABC, abstractmethod

from pandas import DatetimeIndex


class PurgedSplitterPort(ABC):
    @abstractmethod
    def split(self, index: DatetimeIndex) -> list[tuple[slice, slice]]:
        """indexに対して (train_slice, test_slice) のリストを返す"""
        raise NotImplementedError
