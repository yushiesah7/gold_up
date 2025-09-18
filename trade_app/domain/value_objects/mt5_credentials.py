from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


class InvalidCredentialsError(ValueError):
    """MT5認証情報の不備。"""

    pass


@dataclass(frozen=True, slots=True)
class MT5Credentials:
    """
    MT5認証VO：正当性検証を内包し、アプリ全体で安全に使い回す。
    """

    __responsibility__: ClassVar[str] = "MT5認証情報の妥当性検証と保持"

    account: int
    password: str
    server: str

    def __post_init__(self) -> None:
        if self.account <= 0:
            raise InvalidCredentialsError("Account number must be positive")
        if not self.password:
            raise InvalidCredentialsError("Password is required")
        if not self.server:
            raise InvalidCredentialsError("Server name is required")

    @classmethod
    def from_env_vars(
        cls,
        account_str: str | None,
        password: str | None,
        server: str | None,
    ) -> MT5Credentials:
        if not account_str:
            raise InvalidCredentialsError("MT5__ACCOUNT is required")
        if not password:
            raise InvalidCredentialsError("MT5__PASSWORD is required")
        if not server:
            raise InvalidCredentialsError("MT5__SERVER is required")
        try:
            account = int(account_str)
        except ValueError as e:
            raise InvalidCredentialsError(f"Invalid account: {account_str}") from e
        return cls(account=account, password=password, server=server)
