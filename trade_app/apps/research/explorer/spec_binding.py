from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def bind_params_to_spec(spec: Any, params: Mapping[str, Any]) -> Any:
    """
    spec内の文字列 "{{key}}" を params[key] で置換。
    - 値が完全一致 "{{key}}" の場合は型を保った値を返す
    - 文字列の一部に含まれる場合は str 置換
    - dict/list/str を再帰的に辿る
    """
    if isinstance(spec, dict):
        # 辞書キーも置換対象にする
        new_dict: dict[Any, Any] = {}
        for k, v in spec.items():
            new_k: Any = k
            if isinstance(k, str):
                # 文字列キーにも再帰適用（完全一致/部分一致の両方対応）
                new_k = bind_params_to_spec(k, params)
                if not isinstance(new_k, str):
                    # 置換結果が非文字列になった場合はキーとして使えるよう文字列化
                    new_k = str(new_k)
            new_dict[new_k] = bind_params_to_spec(v, params)
        return new_dict

    if isinstance(spec, list):
        return [bind_params_to_spec(x, params) for x in spec]
    if isinstance(spec, str):
        s = spec
        # 完全一致なら型保持
        if s.startswith("{{") and s.endswith("}}") and s.count("{{") == 1 and s.count("}}") == 1:
            key = s[2:-2].strip()
            if key in params:
                return params[key]
            return spec
        # 部分置換は文字列化
        out = s
        for k, v in params.items():
            out = out.replace("{{" + k + "}}", str(v))
        return out
    return spec
