from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd
import pytz

from trade_app.config.defaults import SESSIONS_PRESETS
from trade_app.domain.ports.session_policy import SessionPolicyPort


def _parse_hhmm(s: str) -> tuple[int, int]:
    h, m = s.split(":")
    return int(h), int(m)


def _mask_for_windows(index_utc: pd.DatetimeIndex, windows: list[Mapping[str, Any]]) -> pd.Series:
    if index_utc.tz is None:
        # UTC前提（上位のOHLCVはUTC aware契約）
        index_utc = index_utc.tz_localize("UTC")

    mask = pd.Series(False, index=index_utc)
    for w in windows:
        if w.get("type") == "all":
            return pd.Series(True, index=index_utc)

        if w.get("type") != "window":
            continue

        tz = w.get("tz", "UTC")
        local_idx = index_utc.tz_convert(pytz.timezone(tz))  # DSTはtz_convertが吸収
        sh, sm = _parse_hhmm(str(w["start"]))
        eh, em = _parse_hhmm(str(w["end"]))
        start_sec = sh * 3600 + sm * 60
        end_sec = eh * 3600 + em * 60

        # Series化して index をUTCに合わせる（以降の比較結果も Series になる）
        secs = pd.Series(
            local_idx.hour * 3600 + local_idx.minute * 60 + local_idx.second,
            index=index_utc,
            dtype=int,
        )
        if start_sec <= end_sec:
            m = (secs >= start_sec) & (secs < end_sec)  # [start, end)
        else:
            # 日跨ぎ（例 22:00-06:00）
            m = (secs >= start_sec) | (secs < end_sec)
        # 異TZウィンドウのOR（例: 複数市場をまたぐ）
        mask = mask | m

    return mask


class DefaultSessionPolicy(SessionPolicyPort):
    """プリセットまたは明示ウィンドウから session_active を作る（DST対応）"""

    def make_mask(
        self,
        index_utc: pd.DatetimeIndex,
        *,
        preset: str | None = None,
        tz: str | None = "UTC",
        windows: list[Mapping[str, Any]] | None = None,
    ) -> pd.Series:
        # 優先順：explicit windows > preset > tz=ALLDAY
        if windows:
            return _mask_for_windows(index_utc, windows)
        if preset:
            win = SESSIONS_PRESETS.get(preset.upper())
            if not win:
                raise ValueError(f"unknown session preset: {preset}")
            return _mask_for_windows(index_utc, win)
        # tzだけ指定された場合はALLDAY
        return _mask_for_windows(index_utc, [{"type": "all"}])


# --- FeatureCalculator から呼び出しやすい薄いラッパ ---


def session_feature(
    df: pd.DataFrame,
    *,
    preset: str | None = None,
    tz: str | None = "UTC",
    windows: list[Mapping[str, Any]] | None = None,
) -> pd.Series:
    """Feature kind: 'session' 用の計算関数"""
    mask = DefaultSessionPolicy().make_mask(df.index, preset=preset, tz=tz, windows=windows)
    return mask.rename("session_active")
