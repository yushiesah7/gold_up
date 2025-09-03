from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from autotrade_poc.domain.models.market import Symbol
from autotrade_poc.domain.models.order import (
    OrderRequest,
    OrderResult,
    ModifyResult,
    CloseResult,
    PositionId,
)


class BrokerCredentials:
    """ログイン資格情報。
    実体はアダプタ内でのみ使用可能 (UseCase/Domain は中身を知らない)。
    """

    def __init__(self, *, login: str, password: str, server: str) -> None:
        self.login = login
        self.password = password
        self.server = server


class BrokerPort(ABC):
    """ブローカー発注/口座インタフェース。SDK固有の語彙はここで吸収する。"""

    @abstractmethod
    def connect(self, creds: BrokerCredentials) -> None:  # MT5.initialize/login 相当
        """端末と口座へ接続。失敗時は例外を投げる。"""
        raise NotImplementedError

    @abstractmethod
    def place_order(self, req: OrderRequest) -> OrderResult:
        """発注。SL/TPは req.sl/req.tp を使用。"""
        raise NotImplementedError

    @abstractmethod
    def modify_stops(self, position_id: PositionId, *, sl: float | None, tp: float | None) -> ModifyResult:
        raise NotImplementedError

    @abstractmethod
    def close_position(self, position_id: PositionId, *, volume: float | None = None) -> CloseResult:
        raise NotImplementedError

    @abstractmethod
    def positions(self, symbol: Symbol | None = None) -> Sequence[dict]:
        """ポジション一覧（最小限の辞書。将来DTO化）。"""
        raise NotImplementedError
