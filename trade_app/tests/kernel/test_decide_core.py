import pandas as pd

from trade_app.apps.kernel.decide_core import decide
from trade_app.apps.kernel.plan_contracts import Plan


def test_predicate_and_cross_rules_basic():
    # 小さな価格系列を構築(Indexは整合)
    idx = pd.date_range("2024-01-01", periods=6, freq="D")
    open_ = pd.Series([10, 11, 12, 13, 14, 15], index=idx)
    high = pd.Series([11, 12, 13, 14, 15, 16], index=idx)
    low = pd.Series([9, 10, 11, 12, 13, 14], index=idx)
    close = pd.Series([10, 12, 11, 14, 13, 16], index=idx)

    # 2つの特徴量: rsi(ダミー) と ma(ダミー)
    rsi = pd.Series([30, 35, 40, 55, 65, 70], index=idx)
    ma = pd.Series([10, 10.5, 11, 12, 13, 14], index=idx)
    features = {"rsi": rsi, "ma": ma}

    # Plan:
    # - entries: rsi < 50 かつ close の ma 上抜け
    # - exits: rsi >= 65 または close の ma 下抜け
    plan: Plan = {
        "entries": [
            {
                "kind": "predicate",
                "expr": {"type": "atom", "feature": "rsi", "op": "<", "value": 50},
            },
            {"kind": "cross_over", "left": "close", "right": "ma"},
        ],
        "entries_combine": "and",
        "exits": [
            {
                "kind": "predicate",
                "expr": {"type": "atom", "feature": "rsi", "op": ">=", "value": 65},
            },
            {"kind": "cross_under", "left": "close", "right": "ma"},
        ],
        "exits_combine": "or",
    }

    # 価格系列を予約名で features に含める
    feats = dict(features)
    feats["close"] = close

    result = decide(open_, high, low, close, features=feats, plan=plan)

    # 期待値:
    # クロス上抜けの判定は、前バーと当バーの ma に対する関係で決まる。
    # close: [10, 12, 11, 14, 13, 16]
    #   ma : [10, 10.5, 11, 12, 13, 14]
    # prev<=ma & curr>ma が True になるのは index=1(12>10.5, prev 10<=10.5)
    # と index=3(14>12, prev 11<=12)。ただし entries は同時に rsi<50 が必要。
    # rsi<50 は index 0..2 で成り立つので、entries が True なのは index=1 のみ。
    expected_entries = pd.Series([False, True, False, False, False, False], index=idx)

    # exits は rsi>=65(index 4,5) または cross under(prev>=ma & curr<ma)。
    # close<ma は index=2(11<11 は False)、index=4(13<13 は False) なので発生しない。
    # よって exits は rsi>=65 の index 4,5 で True。
    expected_exits = pd.Series([False, False, False, False, True, True], index=idx)

    assert result["entries"].equals(expected_entries)
    assert result["short_entries"].sum() == 0  # 指定なし -> すべて False
    assert result["exits"].equals(expected_exits)
