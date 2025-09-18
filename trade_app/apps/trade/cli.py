from __future__ import annotations

import typer
from dotenv import load_dotenv

from trade_app.domain.errors import MT5ConnectionError
from trade_app.domain.value_objects.mt5_credentials import (
    InvalidCredentialsError,
    MT5Credentials,
)
from trade_app.infrastructure.adapters.mt5.connection import MT5Adapter
from trade_app.shared.logging import get_logger, setup_logging
from trade_app.shared.settings import MT5EnvSettings

app = typer.Typer(help="MT5 ログイン／接続テスト CLI", no_args_is_help=True)


@app.command("login")
def login(
    mt5_server: str | None = typer.Option(
        None,
        "--mt5-server",
        help="MT5サーバー名（例: XMTrading-MT5 3）",
    ),
    mt5_account: str | None = typer.Option(
        None,
        "--mt5-account",
        help="MT5アカウント番号（数値）",
    ),
    mt5_password: str | None = typer.Option(
        None,
        "--mt5-password",
        help="MT5パスワード",
    ),
) -> None:
    """MT5へログインしてアカウント情報を表示。"""
    try:
        load_dotenv()
        setup_logging(reset_handlers=True, console_output=True, json_format=False)
        logger = get_logger(__name__)

        env = MT5EnvSettings()
        account_str = mt5_account or env.MT5__ACCOUNT
        password = mt5_password or env.MT5__PASSWORD
        server = mt5_server or env.MT5__SERVER

        creds = MT5Credentials.from_env_vars(account_str, password, server)
        adapter = MT5Adapter()
        logger.info("connection_attempting")
        ok = adapter.connect(creds.account, creds.password, creds.server)
        if not ok:
            typer.secho("❌ MT5接続に失敗しました", fg=typer.colors.RED)
            raise typer.Exit(code=1) from None

        info = adapter.get_account_info()
        if info:
            typer.echo("\n✅ MT5接続成功!")
            typer.echo(f"アカウント: {info['login']}")
            typer.echo(f"名前: {info['name']}")
            typer.echo(f"サーバー: {info['server']}")
            typer.echo(f"残高: {info['balance']:.2f} {info['currency']}")
            typer.echo(f"レバレッジ: 1:{info['leverage']}")
        adapter.disconnect()
        typer.echo("\n🔌 接続終了")

    except (InvalidCredentialsError, MT5ConnectionError) as e:
        get_logger(__name__).error("mt5_connection_error", error=str(e))
        typer.secho(f"❌ エラー: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from None
    except Exception as e:
        get_logger(__name__).exception("unexpected_error", error=str(e))
        typer.secho(f"❌ 予期しないエラー: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from None


if __name__ == "__main__":
    app()
