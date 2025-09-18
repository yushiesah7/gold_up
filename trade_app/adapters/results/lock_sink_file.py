from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trade_app.domain.ports.lock_sink import LockSinkPort


class FileLockSinkAdapter(LockSinkPort):
    """spec.lock.json を保存"""

    def write(
        self,
        *,
        best_params: Mapping[str, Any],
        best_score: float,
        features_spec: Mapping[str, Any],
        plan_spec: Mapping[str, Any],
        space: Mapping[str, Any],
        out_dir: Path,
        summary: Mapping[str, Any] | None = None,
        filename: str = "spec.lock.json",
    ) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "best_score": best_score,
            "best_params": dict(best_params),
            "features_spec": features_spec,
            "plan_spec": plan_spec,
            "space": space,
        }
        if isinstance(summary, Mapping):
            payload["summary"] = dict(summary)
        path = out_dir / filename
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
