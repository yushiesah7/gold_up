import pytest

from trade_app.apps.features.pipeline.plan_builder import DefaultPlanBuilder


def test_plan_builder_valid_ops_and_preshift_default():
    spec = {
        "entries": [
            {"op": "gt", "left": "rsi_14", "right": 50},
            {"op": "between", "left": "sma_20", "right": [10, 20]},
        ],
        "short_entries": [{"op": "cross_under", "left": "ema_20", "right": "ema_50"}],
        "exits": [{"op": "le", "left": "atr_14", "right": 2.5}],
    }
    plan = DefaultPlanBuilder().build(spec)
    assert plan.entries[0].pre_shift == 1
    assert plan.entries[1].op == "between"
    assert len(plan.short_entries) == 1
    assert plan.exits[0].op == "le"


def test_plan_builder_rejects_unknown_op():
    bad = {"entries": [{"op": "foo", "left": "x", "right": 1}]}
    with pytest.raises(ValueError, match="unsupported op"):
        DefaultPlanBuilder().build(bad)
