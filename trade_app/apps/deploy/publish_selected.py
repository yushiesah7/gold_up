from __future__ import annotations

"""
publish_selected.py

日次運用準備用のパブリッシュスクリプト。
- 入力: deploy/selected.json（selectorの出力）
- 出力: out_dir/selected.json（そのままコピー）
        out_dir/selected.csv（EA向けにフラット化したCSV、任意）

使い方:
    uv run python -m trade_app.apps.deploy.publish_selected \
        --selected deploy/selected.json \
        --out-dir deploy/live \
        --emit-csv

オプション:
    --emit-csv: CSVも出力（デフォルト: 出力する）
    --no-emit-csv: CSV出力を抑止
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def _load_selected(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _flatten_strategy_to_row(s: dict[str, Any]) -> dict[str, Any]:
    # 基本情報
    row: dict[str, Any] = {
        "symbol": s.get("symbol"),
        "timeframe": s.get("timeframe"),
        "session": s.get("session"),
    }
    rp: dict[str, Any] = s.get("run_params") or {}

    # run_params（一次元にフラット化）
    for k in (
        "fees",
        "slippage",
        "size",
        "size_type",
        "init_cash",
        "leverage",
        "cash_sharing",
        "accumulate",
        "max_entries",
        "max_positions",
        "sl_pct",
        "rr",
        "sl_trail",
        "atr_window",
        "sl_atr_mult",
        "tp_atr_mult",
    ):
        if k in rp:
            row[k] = rp[k]

    # session_preset（ネストを展開）
    sp: dict[str, Any] | None = rp.get("session_preset")
    if isinstance(sp, dict):
        row["session_name"] = sp.get("name")
        row["session_type"] = sp.get("type")
        row["session_start"] = sp.get("start")
        row["session_end"] = sp.get("end")
        row["session_tz"] = sp.get("tz")

    # best_params は列挙（可変幅なので prefix 付与）
    bp: dict[str, Any] = s.get("best_params") or {}
    for k, v in bp.items():
        row[f"param__{k}"] = v

    return row


def _write_csv(strategies: list[dict[str, Any]], csv_path: Path) -> None:
    rows = [_flatten_strategy_to_row(s) for s in strategies]
    # 列順は全行のキー集合順（安定化のためソート）
    fieldnames: list[str] = sorted({k for r in rows for k in r.keys()})
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _run(selected: Path, out_dir: Path, emit_csv: bool) -> int:
    data = _load_selected(selected)
    strategies = data.get("strategies") or []

    out_dir.mkdir(parents=True, exist_ok=True)

    # JSONをそのままコピー
    (out_dir / "selected.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # CSV（任意）
    if emit_csv:
        _write_csv(strategies, out_dir / "selected.csv")

    print(f"published JSON -> {out_dir / 'selected.json'}")
    if emit_csv:
        print(f"published CSV  -> {out_dir / 'selected.csv'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Publish selected strategies to live dir.")
    p.add_argument("--selected", type=Path, default=Path("deploy/selected.json"))
    p.add_argument("--out-dir", type=Path, default=Path("deploy/live"))
    g = p.add_mutually_exclusive_group()
    g.add_argument("--emit-csv", dest="emit_csv", action="store_true", help="emit CSV")
    g.add_argument("--no-emit-csv", dest="emit_csv", action="store_false", help="no CSV")
    p.set_defaults(emit_csv=True)
    args = p.parse_args(argv)
    return _run(args.selected, args.out_dir, args.emit_csv)


if __name__ == "__main__":
    raise SystemExit(main())
