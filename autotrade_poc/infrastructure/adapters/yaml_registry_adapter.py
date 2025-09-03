from __future__ import annotations

from pathlib import Path
from typing import Sequence

import yaml

from autotrade_poc.ports.registry_port import RegistryPort
from autotrade_poc.domain.models.spec import LiveSpec


class YAMLRegistryAdapter(RegistryPort):
    """指定ディレクトリ配下の *.yaml / *.yml を列挙し、LiveSpec へ厳密変換。
    - Pydantic v2: `LiveSpec.model_validate(obj)` を使用。
    - YAML は `safe_load` のみ利用（安全性確保）。
    """

    def __init__(self, *, yaml_dir: str) -> None:
        self.yaml_dir = yaml_dir

    def load_live_specs(self) -> Sequence[LiveSpec]:
        base = Path(self.yaml_dir)
        if not base.exists() or not base.is_dir():
            return []
        specs: list[LiveSpec] = []
        for path in sorted(base.rglob("*.y*ml")):
            text = path.read_text(encoding="utf-8")
            data = yaml.safe_load(text)
            if data is None:
                continue
            # 単一/複数いずれにも対応
            if isinstance(data, list):
                for obj in data:
                    specs.append(LiveSpec.model_validate(obj))
            else:
                specs.append(LiveSpec.model_validate(data))
        return specs
