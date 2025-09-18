from __future__ import annotations

"""
validate_selected.py

EA（MT5/MQL）投入前に deploy/selected.json のスキーマを検証する簡易スクリプト。
- 使い方:
    uv run python validate_selected.py --path deploy/selected.json --strict

- 検証内容（デフォルト）:
    strategies[*].symbol: str
    strategies[*].timeframe: str
    strategies[*].session: str
    strategies[*].best_params: dict
    strategies[*].run_params: dict
      - fees: number
      - slippage: number
      - size: number
      - size_type: str
      - init_cash: number（int/floatどちらもOK）
      - leverage: number
      - cash_sharing: bool
      - accumulate: bool
      - max_entries: number
      - max_positions: number
      - session_preset: { name,type,start,end,tz: str }
      - 追加の任意キー（例: sl_pct, rr, sl_trail, atr_window, sl_atr_mult, tp_atr_mult）は strict でない限り存在不要

- --strict オプション:
    SL/TP の方式に応じた必須キーを検査（例: 固定SL/TPの場合 sl_pct/rr、ATRトレールの場合 sl_trail/atr_window など）

戻り値: 正常時 0、検証NGで 1。
"""

import argparse
import json
from pathlib import Path
from typing import Any

NumberLike = (int, float)


def _require(d: dict, key: str, typ: type | tuple[type, ...]) -> Any:
    if key not in d:
        raise AssertionError(f"missing key: {key}")
    v = d[key]
    if typ is float:
        if not isinstance(v, NumberLike):
            raise AssertionError(f"type mismatch: {key} expected number, got {type(v).__name__}")
    elif not isinstance(v, typ):
        raise AssertionError(f"type mismatch: {key} expected {typ}, got {type(v).__name__}")
    return v


def _validate_session_preset(sp: dict[str, Any]) -> None:
    _require(sp, "name", str)
    _require(sp, "type", str)
    _require(sp, "start", str)
    _require(sp, "end", str)
    _require(sp, "tz", str)


def _validate_run_params(rp: dict[str, Any], strict: bool) -> None:
    _require(rp, "fees", float)
    _require(rp, "slippage", float)
    _require(rp, "size", float)
    _require(rp, "size_type", str)
    _require(rp, "init_cash", float)
    _require(rp, "leverage", float)
    _require(rp, "cash_sharing", bool)
    _require(rp, "accumulate", bool)
    _require(rp, "max_entries", float)
    _require(rp, "max_positions", float)
    sp = _require(rp, "session_preset", dict)
    _validate_session_preset(sp)

    if strict:
        # 代表的な2系統のどちらかが満たされることを要求（固定SL/TP or ATRトレール）
        has_fixed = all(k in rp for k in ("sl_pct", "rr"))
        has_atr = (rp.get("sl_trail") is True) and all(
            k in rp for k in ("atr_window", "sl_atr_mult", "tp_atr_mult")
        )
        if not (has_fixed or has_atr):
            raise AssertionError(
                "strict mode: either fixed SL/TP (sl_pct, rr) or ATR trail (sl_trail=true, atr_window, sl_atr_mult, tp_atr_mult) must be present"
            )


def validate_selected(path: Path, strict: bool) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    strategies = _require(data, "strategies", list)
    if not strategies:
        raise AssertionError("strategies is empty")

    for i, s in enumerate(strategies):
        try:
            _require(s, "symbol", str)
            _require(s, "timeframe", str)
            _require(s, "session", str)
            _require(s, "best_params", dict)
            rp = _require(s, "run_params", dict)
            _validate_run_params(rp, strict)
        except AssertionError as e:
            raise AssertionError(f"strategy[{i}]: {e}") from e


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate deploy/selected.json schema for EA.")
    parser.add_argument(
        "--path", type=Path, default=Path("deploy/selected.json"), help="Path to selected.json"
    )
    parser.add_argument(
        "--strict", action="store_true", help="Enable strict checks for SL/TP policy"
    )
    args = parser.parse_args()

    try:
        validate_selected(args.path, args.strict)
        print(f"Validation OK: {args.path}")
        return 0
    except Exception as e:
        print(f"Validation NG: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
