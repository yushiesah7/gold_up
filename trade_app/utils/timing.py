from __future__ import annotations

import csv
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter


@dataclass
class TimingLogger:
    path: Path
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.enabled:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        init = not self.path.exists()
        if init:
            with self.path.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(
                    [
                        "ts_utc",
                        "phase",
                        "secs",
                        "symbol",
                        "timeframe",
                        "session",
                        "notes",
                    ]
                )

    def write(
        self,
        phase: str,
        secs: float,
        *,
        symbol: str | None = None,
        timeframe: str | None = None,
        session: str | None = None,
        notes: str = "",
    ) -> None:
        if not self.enabled:
            return
        with self.path.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    phase,
                    f"{secs:.6f}",
                    symbol or "",
                    timeframe or "",
                    session or "",
                    notes,
                ]
            )


@contextmanager
def time_phase(logger: TimingLogger, phase: str, **meta):
    if not getattr(logger, "enabled", True):
        # Disabled: no perf counter, no file I/O
        yield
        return
    t0 = perf_counter()
    try:
        yield
    finally:
        logger.write(phase, perf_counter() - t0, **meta)


def build_logger() -> TimingLogger:
    # オン/オフは GDX_TIMINGS で制御（既定 OFF）。
    # truthy: 1/true/on/yes（大文字小文字無視）
    flag = os.getenv("GDX_TIMINGS", "0").strip().lower()
    enabled = flag in {"1", "true", "on", "yes"}
    # 出力先は GDX_TIMINGS_CSV（有効時のみ使用）。既定は runs/timings.csv
    out = os.getenv("GDX_TIMINGS_CSV", "runs/timings.csv") if enabled else "runs/timings.csv"
    return TimingLogger(Path(out), enabled=enabled)
