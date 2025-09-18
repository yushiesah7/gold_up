from __future__ import annotations

from collections.abc import Mapping
from contextlib import suppress
from typing import Any, ClassVar

import MetaTrader5 as mt5

from trade_app.domain.errors import MT5ConnectionError
from trade_app.domain.ports.execution import MT5ConnectionPort
from trade_app.shared.logging import get_logger


class MT5Adapter(MT5ConnectionPort):
    """
    MetaTrader5 を包む Adapter。外部例外/型を内側に漏らさない。
    """

    __responsibility__: ClassVar[str] = "MT5 APIの実装（Port実装）とエラー変換"
    __debt_reason__: ClassVar[dict[str, str]] = {
        "reason": "将来のベンダ差し替え余地（cTrader等）確保のため層分離",
        "owner": "architecture",
        "until": "2026-01-01",
    }

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._connected = False

    def connect(self, account: int, password: str, server: str) -> bool:
        self._logger.info("mt5_connection_attempting", server=server, account=account)
        try:
            if not mt5.initialize():
                code, message = self._decode_last_error()
                self._logger.error("mt5_init_failed", code=code, message=message)
                raise MT5ConnectionError(f"MT5 initialize failed: {code} {message}")

            if not mt5.login(account, password, server):
                code, message = self._decode_last_error()
                self._logger.error(
                    "mt5_login_failed",
                    account=account,
                    server=server,
                    code=code,
                    message=message,
                )
                mt5.shutdown()
                raise MT5ConnectionError(f"MT5 login failed: {code} {message}")

            info = mt5.account_info()
            if not info:
                self._logger.error("mt5_account_info_failed")
                mt5.shutdown()
                raise MT5ConnectionError("Failed to retrieve account info")

            self._connected = True
            self._logger.info(
                "mt5_connected",
                account=info.login,
                name=info.name,
                server=info.server,
                balance=info.balance,
                currency=info.currency,
                leverage=info.leverage,
                trade_mode=info.trade_mode,
            )
            return True
        except Exception as e:
            self._logger.exception("mt5_connection_error", error=str(e))
            with suppress(Exception):
                mt5.shutdown()
            raise

    def disconnect(self) -> None:
        if self._connected:
            try:
                mt5.shutdown()
                self._connected = False
                self._logger.info("mt5_disconnected")
            except Exception as e:
                self._logger.warning("mt5_disconnect_error", error=str(e))

    def is_connected(self) -> bool:
        return self._connected

    def get_account_info(self) -> Mapping[str, Any] | None:
        if not self._connected:
            return None
        try:
            info = mt5.account_info()
            if info:
                return {
                    "login": info.login,
                    "name": info.name,
                    "server": info.server,
                    "balance": info.balance,
                    "equity": info.equity,
                    "margin": info.margin,
                    "margin_free": info.margin_free,
                    "currency": info.currency,
                    "leverage": info.leverage,
                    "trade_mode": info.trade_mode,
                }
            return None
        except Exception as e:
            self._logger.exception("get_account_info_error", error=str(e))
            return None

    def get_symbol_info(self, symbol: str) -> Mapping[str, Any] | None:
        if not self._connected:
            self._logger.warning("symbol_info_not_connected", symbol=symbol)
            return None
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                self._logger.warning("symbol_info_not_found", symbol=symbol)
                return None
            return {
                "symbol": symbol,
                "point": info.point,
                "digits": info.digits,
                "spread": info.spread,
                "tick_size": info.trade_tick_size,
                "contract_size": info.trade_contract_size,
            }
        except Exception as e:
            self._logger.exception("symbol_info_error", symbol=symbol, error=str(e))
            return None

    @staticmethod
    def _decode_last_error() -> tuple[int | str, str | str]:
        try:
            code, message = mt5.last_error()
            return code, message
        except Exception:
            return "unknown", "unknown"
