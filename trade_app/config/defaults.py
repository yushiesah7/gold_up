from __future__ import annotations

# 最小構成が未指定のときに使う既定（アプリ層に集約）
DEFAULT_SYMBOLS = ["EURUSD", "USDJPY", "XAUUSD"]
DEFAULT_TIMEFRAMES = ["m15", "h1", "h4"]

# セッションプリセット（DSTは各TZのルールに従い自動調整される）
SESSIONS_PRESETS = {
    "ALLDAY": [{"type": "all"}],  # 24時間
    "TOKYO": [{"type": "window", "start": "09:00", "end": "15:00", "tz": "Asia/Tokyo"}],
    "LONDON": [{"type": "window", "start": "08:00", "end": "17:00", "tz": "Europe/London"}],
    "NY": [{"type": "window", "start": "09:30", "end": "16:00", "tz": "America/New_York"}],
}

# ポジション上限の既定
POSITION_LIMITS = {
    "per_symbol": 1,
    "global_max": None,  # 未来対応（今は未使用）
}
