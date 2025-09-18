import pandas as pd

from trade_app.apps.research.policies.position_limiter import limit_positions


def test_limit_positions_cap1_exit_first():
    idx = pd.date_range("2024-01-01", periods=6, freq="h", tz="UTC")
    entries = pd.Series([1, 1, 0, 1, 0, 0], index=idx, dtype=bool)
    exits = pd.Series([0, 0, 1, 0, 0, 1], index=idx, dtype=bool)
    gated = limit_positions(entries, exits, max_positions=1, exit_first=True)
    # 0h: 入る -> open=1
    # 1h: 入りたいが枠無し -> False
    # 2h: 出る -> open=0
    # 3h: 入る -> open=1
    # 5h: 出る -> open=0
    assert gated.tolist() == [True, False, False, True, False, False]


def test_limit_positions_cap2():
    idx = pd.date_range("2024-01-01", periods=5, freq="h", tz="UTC")
    entries = pd.Series([1, 1, 1, 0, 0], index=idx, dtype=bool)
    exits = pd.Series([0, 0, 0, 1, 1], index=idx, dtype=bool)
    gated = limit_positions(entries, exits, max_positions=2)
    # 0h: 入 -> open=1
    # 1h: 入 -> open=2
    # 2h: 入りたいが枠無し -> False
    # 3h: 出 -> open=1
    # 4h: 出 -> open=0
    assert gated.tolist() == [True, True, False, False, False]
