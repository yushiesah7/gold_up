from __future__ import annotations

from typing import Sequence

from configs.settings import AppSettings
from domain.models.spec import LiveSpec
from ports.broker_port import BrokerPort
from ports.marketdata_port import MarketDataPort
from ports.clock_port import ClockPort
from ports.registry_port import RegistryPort
from ports.logger_port import LoggerPort
from usecase.start_autotrade_uc import StartAutoTradeUC


class AppRunner:
    """アプリのエントリポイント。
    - 設定ロード
    - Port実装の組み立て
    - ユースケースの起動
    """

    def __init__(
        self,
        settings: AppSettings,
        broker: BrokerPort,
        marketdata: MarketDataPort,
        clock: ClockPort,
        registry: RegistryPort,
        logger: LoggerPort,
    ) -> None:
        self.settings = settings
        self.broker = broker
        self.marketdata = marketdata
        self.clock = clock
        self.registry = registry
        self.logger = logger

    def run(self) -> None:
        """アプリ全体の起動。YAMLの LiveSpec 群を取得し、自動売買を開始する。
        実処理はUseCaseへ丸投げ（本ファイルは配線のみ）。
        """
        specs: Sequence[LiveSpec] = self.registry.load_live_specs()
        uc = StartAutoTradeUC(
            broker=self.broker,
            marketdata=self.marketdata,
            clock=self.clock,
            logger=self.logger,
        )
        uc.run(specs)
