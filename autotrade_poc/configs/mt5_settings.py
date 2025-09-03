from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class MT5Settings(BaseSettings):
    """MT5 接続設定を環境変数から読み込む。
    - 環境変数名の例: MT5__ACCOUNT, MT5__PASSWORD, MT5__SERVER
    - 機密値はここでのみ扱い、上位層へは `BrokerCredentials` に詰めて渡す。
    - 余計なキーは拒否（extra='forbid'）。
    """

    account: str
    password: str
    server: str

    model_config = SettingsConfigDict(env_prefix="MT5__", env_file=".env", extra="forbid")
