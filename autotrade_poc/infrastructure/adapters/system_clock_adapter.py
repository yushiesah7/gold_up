from __future__ import annotations

from datetime import datetime, timezone
import time as _time

from autotrade_poc.ports.clock_port import ClockPort


class SystemClockAdapter(ClockPort):
    def now(self) -> datetime:
        # UTC基準の aware datetime を返却
        return datetime.now(timezone.utc)

    def sleep_until(self, dt: datetime) -> None:
        now = self.now()
        remain = (dt - now).total_seconds()
        if remain > 0:
            _time.sleep(remain)
