from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from trade_app.domain.services.selection_service import (
    Candidate,
    SelectionCriteria,
    select_top_by_symbol_session,
)

HELP = "Select best strategies from runs and emit deployable config."
EXPECTED_MIN_PARTS = 6  # .../runs/<run>/<SYMBOL>/<timeframe>/<SESSION>/spec.lock.json
KNOWN_TIMEFRAMES = {"m1", "m5", "m15", "m30", "h1", "h4", "d1"}
KNOWN_SESSIONS = {"ALLDAY", "TOKYO", "LONDON", "NY"}


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _infer_triplet_from_path(lock_path: Path) -> tuple[str, str, str]:
    # Expect: .../runs/<run_name>/<SYMBOL>/<timeframe>/<SESSION>/spec.lock.json
    parts = lock_path.parts
    if len(parts) >= EXPECTED_MIN_PARTS:
        return parts[-4], parts[-3], parts[-2]
    return "UNKNOWN", "UNKNOWN", "UNKNOWN"


def _read_lock(p: Path) -> dict[str, Any]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _extract_run_params_from_yaml(yaml_path: Path) -> dict[str, Any] | None:
    try:
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        rp = data.get("run_params")
        if isinstance(rp, dict):
            return rp
    except Exception:
        return None
    return None


def _discover_run_params(
    lock_path: Path, project_root: Path, fallback_yaml: Path | None
) -> dict[str, Any] | None:
    # 1) same directory
    cand = lock_path.parent / "spec.yaml"
    if cand.exists():
        rp = _extract_run_params_from_yaml(cand)
        if rp:
            return rp
    # 2) run root (two levels up from SYMBOL/timeframe/session)
    try:
        run_root = lock_path.parents[3]  # .../runs/<run_name>/...
        cand2 = run_root / "spec.yaml"
        if cand2.exists():
            rp = _extract_run_params_from_yaml(cand2)
            if rp:
                return rp
    except Exception:
        pass
    # 3) fallback path
    if fallback_yaml and fallback_yaml.exists():
        rp = _extract_run_params_from_yaml(fallback_yaml)
        if rp:
            return rp
    return None


def _run(
    runs: Path,
    criteria: Path,
    out: Path,
    pack_dir: Path,
    verbose: bool,
    fallback_run_params: Path | None,
) -> int:
    # Load criteria
    cfg = _load_yaml(criteria)
    sel = SelectionCriteria(
        min_sharpe=float(cfg.get("min_sharpe", 1.0)),
        min_compounded=float(cfg.get("min_compounded", 0.0)),
        min_folds=int(cfg.get("min_folds", 3)),
        min_trades=cfg.get("min_trades"),
        max_left_tail=cfg.get("max_left_tail"),
    )

    # Collect lock files (primary)
    root = runs.resolve()
    lock_files = list(root.rglob("spec.lock.json"))
    if verbose:
        print(f"search root: {root}")
        print(f"exists: {root.exists()} is_dir: {root.is_dir()}")

    # Fallback: derive lock paths from summary.csv if no spec.lock.json found
    if not lock_files:
        if verbose:
            print("no spec.lock.json found via rglob, trying summary.csv fallback")
        project_root = Path.cwd()
        csv_list = list(root.rglob("summary.csv"))
        if verbose:
            print(f"summary.csv files: {len(csv_list)} under {root}")
        for csv_path in csv_list:
            try:
                with csv_path.open("r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        lp = (row.get("lock_path") or "").strip()
                        if not lp:
                            continue
                        norm = lp.replace("\\", "/")
                        p = Path(norm)
                        if not p.is_absolute():
                            if norm.startswith("runs/"):
                                p = (project_root / p).resolve()
                            else:
                                p = (root / p).resolve()
                        if p.name == "spec.lock.json" and p.exists():
                            lock_files.append(p)
            except Exception:
                continue
    if verbose and not lock_files:
        print("still no locks after summary.csv fallback")

    candidates: list[Candidate] = []
    for lf in lock_files:
        rec = _read_lock(lf)
        if not rec:
            continue
        symbol, timeframe, session = _infer_triplet_from_path(lf)
        # filter out invalid triplet early
        if symbol == "UNKNOWN" or timeframe == "UNKNOWN" or session == "UNKNOWN":
            continue
        if timeframe not in KNOWN_TIMEFRAMES:
            continue
        if session not in KNOWN_SESSIONS:
            continue
        summary = rec.get("summary", {}) or {}
        best_params = rec.get("best_params", {}) or {}
        run_params = rec.get("run_params", None)
        if run_params is None:
            # try to discover from spec.yaml nearby or fallback
            run_params = _discover_run_params(lf, Path.cwd(), fallback_run_params)
        candidates.append(
            Candidate(
                symbol=symbol,
                timeframe=timeframe,
                session=session,
                lock_path=str(lf.as_posix()),
                summary=summary,
                best_params=best_params,
                run_params=run_params,
            )
        )

    selected = select_top_by_symbol_session(candidates, sel)

    if verbose:
        print(f"found locks: {len(lock_files)}")
        for i, lf in enumerate(lock_files[:5]):
            print(f"  lock[{i}]: {lf}")
        print(f"candidates passing criteria: {len(selected)} (grouped by symbol/session)")

    # Emit outputs
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "criteria": asdict(sel),
        "strategies": [
            {
                "symbol": c.symbol,
                "timeframe": c.timeframe,
                "session": c.session,
                "best_params": dict(c.best_params),
                "run_params": dict(c.run_params) if c.run_params else None,
                "lock_path": c.lock_path,
                "summary": c.summary,
            }
            for c in selected
        ],
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    bundle = pack_dir / ts / "selected.json"
    bundle.parent.mkdir(parents=True, exist_ok=True)
    bundle.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"selected -> {out}")
    print(f"bundle -> {bundle}")
    return 0


def main(argv: list[str] | None = None) -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description=HELP)
    parser.add_argument("--runs", "-r", type=Path, default=Path("runs"), help="Runs root dir")
    parser.add_argument(
        "--criteria", type=Path, default=Path("configs/deploy/selection.yaml"), help="Criteria YAML"
    )
    parser.add_argument(
        "--out", type=Path, default=Path("deploy/selected.json"), help="Output JSON path"
    )
    parser.add_argument(
        "--pack-dir", type=Path, default=Path("deploy/packs"), help="Bundle root dir"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose diagnostics")
    parser.add_argument(
        "--fallback-run-params",
        type=Path,
        default=None,
        help="Fallback YAML to take run_params from when lock lacks run_params.",
    )
    args = parser.parse_args(argv)
    return _run(
        args.runs, args.criteria, args.out, args.pack_dir, args.verbose, args.fallback_run_params
    )


if __name__ == "__main__":
    sys.exit(main())
