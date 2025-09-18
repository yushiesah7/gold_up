import pandas as pd
import pytz

from trade_app.apps.research.splitters.purged_kfold import PurgedKFoldSplitter


def test_purged_kfold_basic_windows():
    idx = pd.date_range("2024-01-01", periods=100, freq="h", tz=pytz.UTC)
    sp = PurgedKFoldSplitter(n_splits=5, embargo=2)
    folds = sp.split(idx)
    assert len(folds) == 5
    # 連続かつカバレッジ確認
    assert folds[0][0] == idx[0]
    assert folds[-1][1] == idx[-1]
    # 単調増加
    for i in range(1, len(folds)):
        assert folds[i][0] > folds[i - 1][0]
