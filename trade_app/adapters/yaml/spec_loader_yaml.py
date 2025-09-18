from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from trade_app.domain.ports.spec_loader import SpecLoaderPort


class YamlSpecLoader(SpecLoaderPort):
    """YAMLから features/plan を読み込む。トップレベル keys: features / plan"""

    def load(self, path: Path) -> tuple[Mapping[str, Mapping], Mapping]:
        with path.open("r", encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}
        features = data.get("features", {}) or {}
        plan = data.get("plan", {}) or {}
        if not isinstance(features, dict) or not isinstance(plan, dict):
            raise ValueError("YAML structure must have mapping 'features' and 'plan'")
        return features, plan
