import json
from pathlib import Path

from trade_app.adapters.results.lock_sink_file import FileLockSinkAdapter


def test_lock_sink_writes_json(tmp_path: Path):
    sink = FileLockSinkAdapter()
    path = sink.write(
        best_params={"rsi.length": 14},
        best_score=1.23,
        features_spec={"rsi_14": {"kind": "rsi", "on": "close", "params": {"length": 14}}},
        plan_spec={"entries": [{"op": "gt", "left": "rsi_14", "right": 50, "pre_shift": 1}]},
        space={"rsi.length": {"type": "int", "low": 5, "high": 30}},
        out_dir=tmp_path,
    )
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["best_params"]["rsi.length"] == 14
    assert data["best_score"] == 1.23
