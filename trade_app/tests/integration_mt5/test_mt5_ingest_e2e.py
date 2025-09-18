import os
from pathlib import Path

import pandas as pd
import pytest
import pytz
from dotenv import load_dotenv

from trade_app.adapters.mt5.mt5_history_adapter import MT5HistorySourceAdapter
from trade_app.adapters.parquet.parquet_sink_adapter import ParquetSinkAdapter
from trade_app.apps.ingest.usecases import ingest_history_to_parquet

pytest.importorskip("MetaTrader5")
pytest.importorskip("pyarrow")

# .env を読み込む（プロジェクトルート想定）
load_dotenv()

MT5_E2E = os.getenv("MT5_E2E") == "1"
server = os.getenv("MT5__SERVER")
login = os.getenv("MT5__ACCOUNT")
pwd = os.getenv("MT5__PASSWORD")
symbol = os.getenv("MT5__SYMBOL", "EURUSD")

reason = "MT5_E2E!=1 または MT5資格情報が未設定のためskip"
pytestmark = pytest.mark.skipif(not (MT5_E2E and server and login and pwd), reason=reason)


def test_mt5_to_parquet_real(tmp_path: Path):
    """
    MT5から実データを取得してParquetに書き出す
    $env:MT5_E2E="1" ; uv run pytest trade_app/tests/integration_mt5/test_mt5_ingest_e2e.py
    """
    import MetaTrader5 as mt5  # noqa: PLC0415

    # --- MT5ログイン ---
    assert mt5.initialize(), "MT5 initialize failed"
    try:
        ok = mt5.login(login=int(login), password=pwd, server=server)
        assert ok, "MT5 login failed"

        # --- 実データ取得→正規化→Parquet書き出し ---
        src = MT5HistorySourceAdapter()  # 実アダプタ（DIなし）
        sink = ParquetSinkAdapter()  # 実Parquet

        end = pd.Timestamp.now(tz=pytz.UTC)
        start = end - pd.Timedelta(days=7)

        res_list = ingest_history_to_parquet(
            source=src,
            sink=sink,
            symbols=[symbol],
            timeframe="h1",
            start=start,
            end=end,
            base_dir=tmp_path,
            origin_tz="UTC",
            target_tz="UTC",
        )

        assert len(res_list) == 1
        res = res_list[0]
        assert res.rows > 0, "取得行数が0"
        assert res.path.exists(), "Parquetが書き出されていない"

        # 読み戻して契約確認（UTC index / 列名）
        back = pd.read_parquet(res.path)
        assert back.index.tz is not None
        assert {"open", "high", "low", "close"}.issubset(back.columns)

    finally:
        mt5.shutdown()
