from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MT5EnvSettings(BaseSettings):
    """環境変数からMT5接続設定を取得（.env対応）"""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    MT5__SERVER: str = Field(default="")
    MT5__ACCOUNT: str = Field(default="")
    MT5__PASSWORD: str = Field(default="")


class AccountInfo(BaseModel):
    login: int
    name: str
    server: str
    balance: float
    currency: str
