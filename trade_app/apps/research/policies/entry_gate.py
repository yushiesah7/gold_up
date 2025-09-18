from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from trade_app.apps.features.indicators.session import DefaultSessionPolicy
from trade_app.apps.research.policies.position_limiter import limit_positions


class CombinedEntryGate:
    """
    セッション(DST対応)＆ポジション上限制御を entries に適用する合成ゲート。
    - context = {"session": "LONDON" など, "max_positions": 1 など}
    - features に 'session_active' 列があればそれを優先。無い場合は session を使って生成して適用。
    """

    def __init__(self, *, default_max_positions: int | None = 1):
        self.default_max_positions = default_max_positions

    def gate(
        self,
        *,
        entries: pd.Series,
        exits: pd.Series,
        features: pd.DataFrame,
        context: Mapping[str, Any] | None = None,
    ) -> pd.Series:
        ctx = dict(context or {})
        raw_max = ctx.get("max_positions", self.default_max_positions)
        max_pos = int(raw_max) if raw_max is not None else None

        # セッションマスクの決定
        if "session_active" in features.columns:
            session_mask = features["session_active"].fillna(False).astype(bool)
        else:
            preset = ctx.get("session")
            if preset:
                session_mask = DefaultSessionPolicy().make_mask(features.index, preset=preset)
            else:
                session_mask = pd.Series(True, index=features.index, dtype=bool)

        # まずセッションでゲート
        gated = entries.fillna(False).astype(bool) & session_mask

        # 次に同時保有数でゲート
        if max_pos is not None:
            gated = limit_positions(gated, exits, max_positions=max_pos, exit_first=True)
        return gated
