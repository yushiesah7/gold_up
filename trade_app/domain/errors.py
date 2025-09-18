from __future__ import annotations


class MT5ConnectionError(Exception):
    """MT5接続失敗・API障害などのラップ例外。"""

    __responsibility__ = "外部例外のドメイン例外への変換"
