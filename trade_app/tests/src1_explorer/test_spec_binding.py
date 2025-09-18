from trade_app.apps.research.explorer.spec_binding import bind_params_to_spec


def test_bind_params_to_spec_replaces_placeholders():
    params = {"rsi.length": 14, "bb.mult": 2.0}
    spec = {
        "rsi_{{rsi.length}}": {
            "kind": "rsi",
            "on": "close",
            "params": {"length": "{{rsi.length}}"},
        },
        "bb_20_{{bb.mult}}": {
            "kind": "bb",
            "on": "close",
            "params": {"window": 20, "mult": "{{bb.mult}}"},
        },
    }
    out = bind_params_to_spec(spec, params)
    assert "rsi_14" in out and out["rsi_14"]["params"]["length"] == 14
    assert "bb_20_2.0" in out and out["bb_20_2.0"]["params"]["mult"] == 2.0
