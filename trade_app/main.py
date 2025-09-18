from __future__ import annotations

import typer

from trade_app.apps.trade.cli import app as trade_cli_app

"""
ルート集約Typer。
例: python -m trade_app.main trade login
"""

app = typer.Typer(help="golden-dragon-generator root CLI", no_args_is_help=True)

# `trade` サブコマンド配下に既存の CLI をぶら下げる
app.add_typer(trade_cli_app, name="trade", help="Trading runtime commands")


if __name__ == "__main__":
    app()
