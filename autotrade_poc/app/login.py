from __future__ import annotations

from autotrade_poc.configs.mt5_settings import MT5Settings
from autotrade_poc.ports.broker_port import BrokerCredentials, BrokerPort


def login_mt5_from_env(broker: BrokerPort) -> None:
    """Read MT5 credentials from environment (.env) and connect via BrokerPort.

    - Uses MT5Settings (pydantic-settings) with env_prefix "MT5__".
    - Builds BrokerCredentials and calls broker.connect().
    - Any failure should be raised by the adapter or pydantic; caller handles it.
    """
    s = MT5Settings()  # loads from env/.env with extra='forbid'
    creds = BrokerCredentials(login=s.account, password=s.password, server=s.server)
    broker.connect(creds)
