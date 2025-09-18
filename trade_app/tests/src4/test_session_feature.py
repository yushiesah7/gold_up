import pandas as pd
import pytz

from trade_app.apps.features.indicators.session import session_feature


def test_session_all_day_true():
    idx = pd.date_range("2024-03-01", periods=24, freq="h", tz=pytz.UTC)
    df = pd.DataFrame(index=idx)
    s = session_feature(df, preset="ALLDAY")
    assert s.all()


def test_session_dst_london_window():
    # 英国夏時間開始直前〜直後（2024-03-31 DST開始）
    idx = pd.date_range("2024-03-31 00:00", periods=12, freq="h", tz=pytz.UTC)
    df = pd.DataFrame(index=idx)
    # ロンドン 08:00-17:00 をマスク
    s = session_feature(df, preset="LONDON")
    # 各ローカル時間が条件内にTrue（ズレなく動くことを簡便に確認）
    local = idx.tz_convert("Europe/London")
    # DatetimeIndex.hour は配列を返すため、Seriesに揃えて比較する
    within = pd.Series((local.hour >= 8) & (local.hour < 17), index=idx, dtype=bool)
    pd.testing.assert_index_equal(s.index, within.index)
    pd.testing.assert_series_equal(s.astype(bool), within, check_names=False)


def test_session_custom_window_cross_midnight_tokyo():
    idx = pd.date_range("2024-01-01 12:00", periods=8, freq="h", tz=pytz.UTC)
    df = pd.DataFrame(index=idx)
    win = [{"type": "window", "start": "22:00", "end": "02:00", "tz": "Asia/Tokyo"}]
    s = session_feature(df, windows=win)
    # 22-24 or 0-2（東京ローカル）
    local = idx.tz_convert("Asia/Tokyo")
    within = pd.Series(
        ((local.hour * 3600 + local.minute * 60) >= 22 * 3600)
        | ((local.hour * 3600 + local.minute * 60) < 2 * 3600),
        index=idx,
        dtype=bool,
    )
    pd.testing.assert_index_equal(s.index, within.index)
    pd.testing.assert_series_equal(s.astype(bool), within, check_names=False)
