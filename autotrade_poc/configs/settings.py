from __future__ import annotations

from pydantic import BaseModel


class AppSettings(BaseModel):
    """アプリ横断設定（ログ、リトライ、YAMLディレクトリなど）。
    将来は `pydantic_settings.BaseSettings` に置き換え可能。
    """

    yaml_dir: str
    # リトライやスリッページ上限等の将来設定はここへ
