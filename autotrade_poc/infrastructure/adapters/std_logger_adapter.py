from __future__ import annotations

import logging

from autotrade_poc.ports.logger_port import LoggerPort


class StdLoggerAdapter(LoggerPort):
    def __init__(self, name: str = "autotrade") -> None:
        self._logger = logging.getLogger(name)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            fmt = logging.Formatter(fmt="%(asctime)s %(levelname)s %(name)s - %(message)s")
            handler.setFormatter(fmt)
            self._logger.addHandler(handler)
        self._logger.setLevel(logging.INFO)

    def info(self, msg: str) -> None:
        self._logger.info(msg)

    def error(self, msg: str) -> None:
        self._logger.error(msg)
