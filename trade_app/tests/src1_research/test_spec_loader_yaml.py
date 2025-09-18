from pathlib import Path

import pytest

from trade_app.adapters.yaml.spec_loader_yaml import YamlSpecLoader

yaml = pytest.importorskip("yaml")


def test_yaml_spec_loader_roundtrip(tmp_path: Path):
    p = tmp_path / "spec.yaml"
    p.write_text(
        """
features:
  rsi_14: {kind: rsi, on: close, params: {length: 14}}
  sma_20: {kind: sma, on: close, params: {length: 20}}
plan:
  entries:
    - {op: gt, left: rsi_14, right: 50, pre_shift: 1}
  exits:
    - {op: lt, left: rsi_14, right: 50, pre_shift: 1}
""",
        encoding="utf-8",
    )
    feats, plan = YamlSpecLoader().load(p)
    assert "rsi_14" in feats and "entries" in plan
