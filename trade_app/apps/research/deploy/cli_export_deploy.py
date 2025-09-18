from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

import pandas as pd
import typer

from trade_app.adapters.deploy.ensemble_exporter import SimpleEnsembleExporter
from trade_app.adapters.results.deploy_exporter_file import FileDeployExporterAdapter
from trade_app.apps.research.deploy.exporter import (
    build_deploy_yaml,
    write_yaml,
)

app = typer.Typer(no_args_is_help=True)


@app.command()
def export(
    summary: Annotated[Path, typer.Argument(help="run_batch_explorer が出力した summary.csv")],
    out_dir: Annotated[Path, typer.Option("--out-dir", help="出力ルート")] = Path("./deploy"),
    spec: Annotated[
        Path | None,
        typer.Option("--spec", help="元の spec.yaml（lock に base が無い場合に必須）"),
    ] = None,
    ensemble: Annotated[
        str, typer.Option("--ensemble", help="best/（将来: topk_mean, vote）")
    ] = "best",
    top_k: Annotated[int, typer.Option("--top-k", help="アンサンブル用（未使用）")] = 1,
) -> None:
    """summary.csv を読み、（symbol×TF×session）ごとのデプロイ用YAMLを生成"""
    exporter = FileDeployExporterAdapter()
    paths: Sequence[Path] = exporter.export_configs(
        summary_csv=summary,
        out_dir=out_dir,
        spec_path=spec,
        ensemble=ensemble,
        top_k=top_k,
    )
    typer.echo(f"generated {len(paths)} files under: {out_dir.resolve()}")


@app.command()
def ensemble(
    summary_csv: Annotated[Path, typer.Argument(help="run_batch_explorer の summary.csv")],
    out_dir: Annotated[Path, typer.Option("--out-dir", help="出力先")] = Path("./deploy"),
    ensemble: Annotated[
        str, typer.Option("--ensemble", help="topk_mean:<k> または vote:<k>")
    ] = "topk_mean:3",
) -> None:
    """summary.csv を読み、（symbol×TF×session）毎のアンサンブル記述子（.deploy.json）を生成"""
    mode, _, k_str = ensemble.partition(":")
    if mode not in ("topk_mean", "vote"):
        raise typer.BadParameter("ensemble must be 'topk_mean:<k>' or 'vote:<k>'")
    try:
        k = int(k_str or "3")
    except Exception as e:
        raise typer.BadParameter("k must be int") from e

    df = pd.read_csv(summary_csv)
    rows = df.to_dict(orient="records")
    exp = SimpleEnsembleExporter()
    files = exp.export(rows, mode=mode, k=k, out_dir=str(out_dir))
    typer.echo(json.dumps({"generated": files}, ensure_ascii=False, indent=2))


@app.command()
def export_bundle(
    summary: Annotated[Path, typer.Argument(help="runs/summary.csv")],
    spec: Annotated[
        Path | None,
        typer.Option("--spec", help="元の spec.yaml（安全運用: features/plan のベース）"),
    ] = None,
    out_dir: Annotated[Path, typer.Option("--out-dir", help="出力先ディレクトリ")] = Path(
        "./deploy"
    ),
    name: Annotated[str, typer.Option("--name", help="出力ファイル名（拡張子不要）")] = "deploy",
    topk: Annotated[int | None, typer.Option("--topk", help="上位kのみ採用。未指定で全件")] = None,
    fmt: Annotated[str, typer.Option("--format", help="yaml|json")] = "yaml",
) -> None:
    """summary.csv と lock 群から集約 deploy.{yaml|json} を生成する。

    既存の per-symbol YAML 出力（export）とは別に、ひとつのファイルにまとめたい場合のエントリ。
    """
    tree = build_deploy_yaml(summary_csv=summary, spec_path=spec, topk=topk)
    out_dir.mkdir(parents=True, exist_ok=True)
    if fmt.lower() == "yaml":
        out = out_dir / f"{name}.yaml"
        write_yaml(tree, out)
    else:
        out = out_dir / f"{name}.json"
        with out.open("w", encoding="utf-8") as f:
            json.dump(tree, f, ensure_ascii=False, indent=2)
    typer.echo(f"saved: {out}")


def main() -> None:  # pragma: no cover
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
