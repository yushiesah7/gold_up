from __future__ import annotations

import glob
import shutil
from pathlib import Path
from typing import Annotated

import pandas as pd
import typer

app = typer.Typer(no_args_is_help=True)


@app.command()
def bundle(
    runs_glob: Annotated[
        str,
        typer.Option("--runs-glob", help="summary.csv のグロブ（例: .\\runs\\**\\summary.csv）"),
    ],
    out_dir: Annotated[Path, typer.Option("--out-dir", help="出力先ディレクトリ")],
    topk: Annotated[int, typer.Option("--topk", help="上位K件を抽出")] = 10,
    extra_paths: list[str] = typer.Argument(None),  # noqa: B008
) -> None:
    """
    複数ランの summary.csv を集約し、best_score 上位K件を選抜して lock ファイルを out_dir へコピー。
    さらに topk.csv を out_dir に出力する。
    期待する summary.csv の列: [symbol,timeframe,session,best_score,lock_path,status,reason]
    備考: PowerShell 環境ではワイルドカードが展開され追加の位置引数になる場合があるため、
    それら（extra_paths）もファイルリストに含める。
    """
    # 1) グロブで summary.csv を収集
    files = glob.glob(runs_glob, recursive=True)
    # PowerShell 等でワイルドカードが展開された場合の追加引数を吸収
    for extra in extra_paths or []:
        files.append(extra)
    if not files:
        raise typer.BadParameter(f"no summary.csv matched: {runs_glob}")

    # 2) 集約
    frames: list[pd.DataFrame] = []
    for fp in files:
        try:
            df = pd.read_csv(fp)
            # ファイル情報を付与
            df["_summary_path"] = str(Path(fp).resolve())
            frames.append(df)
        except Exception:
            continue
    if not frames:
        raise typer.BadParameter("no readable summary.csv")

    all_df = pd.concat(frames, ignore_index=True)
    # 正常終了のもののみ対象
    all_df = all_df.loc[all_df.get("status", "ok").eq("ok")]

    # 3) スコア順にソートし Top-K
    def _to_float(x) -> float:
        try:
            return float(x)
        except Exception:
            return float("nan")

    all_df["best_score"] = all_df["best_score"].apply(_to_float)
    top = all_df.dropna(subset=["best_score"]).sort_values("best_score", ascending=False).head(topk)

    out_dir.mkdir(parents=True, exist_ok=True)

    # 4) lock をコピー（重複名を避けるため、symbol_timeframe_session_n などに改名）
    copied: list[dict[str, str]] = []
    for i, row in enumerate(top.itertuples(index=False), start=1):
        lock_path = getattr(row, "lock_path", "")
        if not lock_path:
            continue
        src = Path(lock_path)
        if not src.is_absolute():
            src = Path.cwd() / src
        if not src.exists():
            continue
        # 出力ファイル名を整形
        sym = str(getattr(row, "symbol", "SYM"))
        tf = str(getattr(row, "timeframe", "TF"))
        sess = str(getattr(row, "session", "SESS")).replace("/", "-").replace("\\", "-")
        dst_name = f"{i:02d}_{sym}_{tf}_{sess}_lock.json"
        dst = out_dir / dst_name
        shutil.copy2(src, dst)
        copied.append(
            {
                "rank": i,
                "symbol": sym,
                "timeframe": tf,
                "session": sess,
                "best_score": str(getattr(row, "best_score", "")),
                "lock_src": str(src),
                "lock_dst": str(dst),
                "summary_src": str(getattr(row, "_summary_path", "")),
            }
        )

    # 5) topk.csv を出力
    pd.DataFrame.from_records(copied).to_csv(out_dir / "topk.csv", index=False)
    typer.echo(f"Top-{len(copied)} exported to: {out_dir}")


if __name__ == "__main__":  # pragma: no cover
    app()
