from __future__ import annotations

from typing import Sequence

from domain.models.spec import LiveSpec
from ports.broker_port import BrokerPort
from ports.marketdata_port import MarketDataPort
from ports.clock_port import ClockPort
from ports.logger_port import LoggerPort


class StartAutoTradeUC:
    """ライブ仕様 (LiveSpec) 群を入力に、自動売買の主ループを開始する。
    ここでは *構造* のみ定め、動作は後続実装で埋める。
    """

    def __init__(
        self,
        *,
        broker: BrokerPort,
        marketdata: MarketDataPort,
        clock: ClockPort,
        logger: LoggerPort,
    ) -> None:
        self.broker = broker
        self.marketdata = marketdata
        self.clock = clock
        self.logger = logger

    def run(self, specs: Sequence[LiveSpec]) -> None:
        # 将来的には: 各 spec ごとにシンボル/時間帯を監視し、シグナル→発注・管理
        # いまは骨格のみ
        pass
