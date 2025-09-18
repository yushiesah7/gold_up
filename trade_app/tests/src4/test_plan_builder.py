from trade_app.apps.features.pipeline.plan_builder import build_plan_from_dict


def test_plan_builder_minimal():
    spec = {"entries": [{"op": "gt", "left": "rsi_14", "right": 50}]}
    plan = build_plan_from_dict(spec)
    assert plan.entries[0].left == "rsi_14"
    assert plan.entries[0].op == "gt"
    assert plan.entries[0].pre_shift == 1
