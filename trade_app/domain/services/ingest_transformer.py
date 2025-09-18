from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

__all__ = ["normalize_ohlcv"]

# デフォルトの列マッピング（MT5想定）
DEFAULT_MAP: Mapping[str, str] = {
    "time": "time",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "tick_volume": "volume",  # MT5は tick_volume が一般的
}


def normalize_ohlcv(
    raw: pd.DataFrame,
    *,
    colmap: Mapping[str, str] = DEFAULT_MAP,
    origin_tz: str | None = "UTC",
    target_tz: str = "UTC",
) -> pd.DataFrame:
    """
    生データ→正規化OHLCV:
      - 列名を map で標準化し、必須列(open/high/low/close)を強制
      - index=DatetimeIndex（UTC aware）、ソート済み・重複drop
      - すべて小文字化、数値列はfloatに揃える
    """
    if "time" not in colmap:
        raise ValueError("colmap に 'time' が必要です")
    if colmap["time"] not in raw.columns and "time" not in raw.columns:
        raise ValueError("colmap/time が不正または raw に存在しません")

    df = raw.copy()

    # 列抽出＆標準化
    wanted: dict[str, pd.Series] = {}
    for src_key, dst_key in colmap.items():
        if src_key in df.columns:
            wanted[dst_key] = df[src_key]
    df = pd.DataFrame(wanted)

    # 列名を小文字化
    df.columns = [str(c).lower() for c in df.columns]

    # 必須列チェック
    req = {"open", "high", "low", "close"}
    missing = req - set(df.columns)
    if missing:
        raise ValueError(f"必須列が不足: {missing}")

    # index化＆TZ正規化
    time_col = "time" if "time" in df.columns else colmap["time"]
    t = df.pop(time_col) if time_col in df.columns else None
    if t is None:
        raise ValueError("time 列が見つかりません")
    # Series化してから DatetimeIndex へ（MT5はPOSIX秒が多い）
    t = pd.Series(t)
    unit: str | None = None
    if pd.api.types.is_integer_dtype(t) or pd.api.types.is_float_dtype(t):
        unit = "s"  # MT5想定：POSIX秒
    idx = pd.DatetimeIndex(pd.to_datetime(t, unit=unit, utc=False, errors="coerce"))
    if idx.isna().any():
        raise ValueError("time列に変換不能な値があります")
    # tz正規化
    if idx.tz is None:
        if origin_tz is None:
            raise ValueError("naive日時です。origin_tzを指定してください")
        idx = idx.tz_localize(origin_tz)
    if str(idx.tz) != target_tz:
        idx = idx.tz_convert(target_tz)

    df.index = idx
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="first")]

    # 数値化
    for c in ["open", "high", "low", "close", "volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # 不完備行drop
    df = df.dropna(subset=["open", "high", "low", "close"], how="any")

    # 列順
    cols = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
    df = df[cols]

    return df
