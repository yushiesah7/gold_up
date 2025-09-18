from __future__ import annotations

from trade_app.adapters.universe.config_universe import ConfigUniverseAdapter


def test_config_universe_defaults_and_override() -> None:
    uni = ConfigUniverseAdapter()
    assert len(uni.list_symbols()) >= 1
    assert "h1" in uni.list_timeframes()

    uni2 = ConfigUniverseAdapter({"symbols": ["EURUSD"], "timeframes": ["m15"]})
    assert uni2.list_symbols() == ["EURUSD"]
    assert uni2.list_timeframes() == ["m15"]
