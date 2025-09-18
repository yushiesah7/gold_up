from __future__ import annotations

import json
from enum import Enum
from typing import Annotated

import typer

# PLC0415 対策：トップレベルで optional import（未導入環境では None フォールバック）
try:  # pragma: no cover
    from trade_app.adapters.universe.mt5_universe import MT5UniverseAdapter  # type: ignore
except Exception:  # pragma: no cover
    MT5UniverseAdapter = None  # type: ignore

from trade_app.adapters.universe.default_universe import DefaultUniverseAdapter

app = typer.Typer(help="Research / Auto Explore CLI")


class UniverseProvider(str, Enum):
    default = "default"
    mt5 = "mt5"


def _resolve_universe(provider: UniverseProvider, pattern: str):
    if provider == UniverseProvider.mt5:
        if MT5UniverseAdapter is None:
            raise RuntimeError("MT5 provider unavailable (package or terminal not initialized)")
        return MT5UniverseAdapter(pattern=pattern)
    return DefaultUniverseAdapter()


@app.callback(invoke_without_command=True)
def _default_entry(
    ctx: typer.Context,
    provider: Annotated[
        UniverseProvider,
        typer.Option(
            "--provider",
            help="列挙元: default or mt5",
        ),
    ] = UniverseProvider.default,
    pattern: Annotated[
        str,
        typer.Option(
            "--pattern",
            help="MT5 のシンボルフィルタ（symbols_get のパターン）",
        ),
    ] = "*",
    json_out: Annotated[
        bool,
        typer.Option("--json", help="JSONで出力"),
    ] = False,
):
    # サブコマンド未指定時に universe と同等の処理を実行して後方互換を維持
    if ctx.invoked_subcommand is not None:
        return

    uni = _resolve_universe(provider, pattern)
    data = {
        "symbols": list(uni.list_symbols()),
        "timeframes": list(uni.list_timeframes()),
        "sessions": list(uni.list_sessions()),
    }
    output = (
        json.dumps(data, ensure_ascii=False, indent=2)
        if json_out
        else "\n".join(f"{k}: {', '.join(v) if v else '(empty)'}" for k, v in data.items())
    )
    typer.echo(output)


@app.command("universe", help="Universe を列挙（symbols/timeframes/sessions）")
def universe_cmd(
    provider: Annotated[
        UniverseProvider,
        typer.Option(
            "--provider",
            help="列挙元: default or mt5",
        ),
    ] = UniverseProvider.default,
    pattern: Annotated[
        str,
        typer.Option(
            "--pattern",
            help="MT5 のシンボルフィルタ（symbols_get のパターン）",
        ),
    ] = "*",
    json_out: Annotated[
        bool,
        typer.Option("--json", help="JSONで出力"),
    ] = False,
) -> None:
    uni = _resolve_universe(provider, pattern)
    data = {
        "symbols": list(uni.list_symbols()),
        "timeframes": list(uni.list_timeframes()),
        "sessions": list(uni.list_sessions()),
    }
    output = (
        json.dumps(data, ensure_ascii=False, indent=2)
        if json_out
        else "\n".join(f"{k}: {', '.join(v) if v else '(empty)'}" for k, v in data.items())
    )
    typer.echo(output)


if __name__ == "__main__":  # pragma: no cover
    app()
