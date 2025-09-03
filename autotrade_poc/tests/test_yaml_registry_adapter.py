from __future__ import annotations

from pathlib import Path

from autotrade_poc.infrastructure.adapters.yaml_registry_adapter import YAMLRegistryAdapter
from autotrade_poc.domain.models.spec import LiveSpec


def test_yaml_registry_loads_single_file(tmp_path: Path) -> None:
    d = tmp_path / "specs"
    d.mkdir()
    (d / "one.yaml").write_text(
        """
market_symbol: {value: "EURUSD"}
market_timeframe: "M15"
ensemble:
  columns: [{label: "rsi=14"}]
  weights: {"rsi=14": 1.0}
  meta: {}
execution:
  order_type: "market"
  price: "nextopen"
  slippage_rate: 0.0001
  fees_rate: 0.0
  size: 0.10
  leverage: 1.0
  init_cash: 100000
stops_mode: "atr_rr"
stops_atr_rr:
  atr_window: [14]
  k_for_sl: [1.0]
  rr: [2.0]
risk:
  per_trade_risk_pct: 0.02
        """,
        encoding="utf-8",
    )
    adapter = YAMLRegistryAdapter(yaml_dir=str(d))
    specs = adapter.load_live_specs()
    assert len(specs) == 1
    spec = specs[0]
    assert isinstance(spec, LiveSpec)
    assert spec.market_symbol.value == "EURUSD"
    assert spec.market_timeframe.value == "M15"


def test_yaml_registry_skips_empty(tmp_path: Path) -> None:
    d = tmp_path / "specs"
    d.mkdir()
    (d / "empty.yaml").write_text("\n", encoding="utf-8")  # 空
    adapter = YAMLRegistryAdapter(yaml_dir=str(d))
    specs = adapter.load_live_specs()
    assert specs == []
