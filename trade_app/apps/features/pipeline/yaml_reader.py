from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import yaml


def load_yaml_to_dict(path: str) -> Mapping[str, Any]:
    """spec.yaml を辞書に（I/O最小。詳細I/OはAdapter化も可能）"""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
