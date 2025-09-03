from __future__ import annotations

import platform
import pytest

MetaTrader5 = pytest.importorskip("MetaTrader5")  # 未インストールならスキップ

is_windows = platform.system().lower().startswith("win")

pytestmark = pytest.mark.skipif(not is_windows, reason="Windows環境のみ実行")


def test_mt5_module_importable() -> None:
    # 形だけの確認（口座接続テストは別途環境が必要なのでスキップ）
    assert hasattr(MetaTrader5, "initialize")
