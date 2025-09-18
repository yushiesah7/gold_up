from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from pandas import DatetimeIndex


@dataclass(frozen=True)
class PurgedWalkForwardSplitter:
    """Purged/Embargo 付きの単純なウォークフォワード分割（バー数ベース）

    - train_size, test_size: いずれも「本数」で指定
    - purge: テスト直前の訓練末尾から除外する本数
    - embargo: テスト直後の本数を次訓練から除外（単純前進のため影響は限定的）
    """

    train_size: int
    test_size: int
    purge: int = 0
    embargo: int = 0

    def split(self, index: DatetimeIndex) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
        """
        OOSの (開始Timestamp, 終了Timestamp) を返す。
        - train区間末尾から purge 本は学習から除外（OOS境界は train_end_raw の直後）
        - embargo は次訓練の構成に影響する概念だが、ここではOOS境界には反映しない
        """
        n = len(index)
        out: list[tuple[pd.Timestamp, pd.Timestamp]] = []
        start = 0
        while True:
            tr_start = start
            tr_end_raw = tr_start + self.train_size
            te_end = tr_end_raw + self.test_size
            if te_end > n:
                break
            # 学習の有効末尾（purge適用後）
            _ = max(tr_start, tr_end_raw - self.purge)
            # OOSの境界は学習raw直後から test_size 本
            oos_start = index[tr_end_raw]
            oos_end = index[te_end - 1]
            out.append((oos_start, oos_end))
            # 次ブロック先頭へ前進
            start = tr_end_raw
        return out
