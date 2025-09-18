from __future__ import annotations

import contextlib
import datetime as dt
import os
from pathlib import Path
from typing import Annotated

import MetaTrader5 as mt5
import pandas as pd
import typer

"""
MT5 → Parquet 一括エクスポート（UTC, OHLCV）

使い方（PowerShell 例）:

  # ルートを指定（推奨: 絶対パス）
  $env:VBT_PARQUET_ROOT = "C:\\data\\parquet"

  # 実行
  uv run python tools/mt5_to_parquet_once.py --symbols EURUSD,USDJPY \
    --timeframes h1,h4 --start 2024-01-01 --end 2024-12-31

必要要件:
- MetaTrader5 (pip)
- pandas, pyarrow
- MT5 ターミナルのインストール/ログイン済み
"""


VBT_PARQUET_ROOT = os.environ.get("VBT_PARQUET_ROOT", "./data/parquet")

app = typer.Typer(no_args_is_help=True)

TIMEFRAME_ENUMS: dict[str, int] = {
    "m15": mt5.TIMEFRAME_M15,
    "h1": mt5.TIMEFRAME_H1,
    "h4": mt5.TIMEFRAME_H4,
}


def _norm_df_from_rates(rates: list[dict] | None) -> pd.DataFrame | None:
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.set_index("time").sort_index()
    if "volume" not in df.columns and "tick_volume" in df.columns:
        df["volume"] = df["tick_volume"]
    cols = [c for c in ("open", "high", "low", "close", "volume") if c in df.columns]
    return df[cols]


@app.command()
def export(
    symbols: Annotated[str, typer.Option(help="カンマ区切りシンボル")] = "EURUSD,USDJPY",
    timeframes: Annotated[str, typer.Option(help="カンマ区切りTF: m15,h1,h4")] = "m15,h1,h4",
    start: Annotated[str, typer.Option(help="UTC開始日 YYYY-MM-DD")] = "2024-01-01",
    end: Annotated[str, typer.Option(help="UTC終了日 YYYY-MM-DD")] = "2024-12-31",
    root_dir: Annotated[Path, typer.Option(help="出力ルート")] = Path(VBT_PARQUET_ROOT),
) -> int:
    start_ts = dt.datetime.fromisoformat(start).replace(tzinfo=dt.UTC)
    end_ts = dt.datetime.fromisoformat(end).replace(tzinfo=dt.UTC)

    root = Path(root_dir)
    root.mkdir(parents=True, exist_ok=True)

    if not mt5.initialize():
        raise RuntimeError("MT5 initialize failed")

    try:
        symbols_list = [s.strip() for s in symbols.split(",") if s.strip()]
        tf_list = [t.strip().lower() for t in timeframes.split(",") if t.strip()]
        tf_pairs: list[tuple[str, int]] = []
        for tf in tf_list:
            if tf not in TIMEFRAME_ENUMS:
                raise ValueError(f"unknown timeframe: {tf}")
            tf_pairs.append((tf, TIMEFRAME_ENUMS[tf]))

        for sym in symbols_list:
            for tf_str, tf_enum in tf_pairs:
                out_dir = root / sym / tf_str
                out_dir.mkdir(parents=True, exist_ok=True)
                rates = mt5.copy_rates_range(sym, tf_enum, start_ts, end_ts)
                df = _norm_df_from_rates(rates)
                if df is None or df.empty:
                    print(f"[WARN] No data: {sym} {tf_str}")
                    continue
                # シングルファイル形式（推奨レイアウトA）
                out_path = out_dir / "ohlcv.parquet"
                df.to_parquet(out_path, engine="pyarrow")
                print(f"[OK] Wrote {out_path} rows={len(df)}")
    finally:
        # mt5.shutdown() が失敗しても無視
        with contextlib.suppress(Exception):
            mt5.shutdown()

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(app())
