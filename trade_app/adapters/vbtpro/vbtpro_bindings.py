from __future__ import annotations

import importlib
import inspect
import json
import os
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def parquet_pull(
    symbols: Iterable[str],
    start: pd.Timestamp | None,
    end: pd.Timestamp | None,
    columns: Sequence[str],
    timeframe: str | None,
    tz: str,
) -> pd.DataFrame:
    """
    VBT PRO の ParquetData.pull を "明示ファイルリスト" で呼ぶ方式。
    - 期待レイアウト: {ROOT}/{symbol}/{timeframe}/ohlcv.parquet
    - 見つからなければ pandas.read_parquet でフォールバック
    - Index は tz-aware(UTC) を想定
    """
    vbt, _ = _import_vbt()

    def _normalize_timeseries(df: pd.DataFrame) -> pd.DataFrame:
        """DatetimeIndexをUTCに正規化し、重複を除去してソート。
        - tz-naiveも強制的にUTCとみなしてtz-aware化
        - インデックスが日時でない場合はto_datetimeを試みる
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            try:
                df.index = pd.to_datetime(df.index, utc=True)
            except Exception:
                return df
        # tz-naive -> UTC
        elif df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        else:
            # 一旦UTCへ
            df.index = df.index.tz_convert("UTC")
        df = df[~df.index.duplicated()].sort_index()
        return df

    # UTC前提の設定（可能なら）
    try:  # pragma: no cover - 実環境依存
        if hasattr(vbt, "settings"):
            vbt.settings["data"]["tz_localize"] = "utc"
            vbt.settings["data"]["tz_convert"] = "utc"
    except Exception:
        pass

    root = Path(os.environ.get("VBT_PARQUET_ROOT", "data/parquet")).resolve()
    tf = timeframe or ""

    files: list[str] = []
    for sym in symbols:
        p = root / sym / tf / "ohlcv.parquet"
        if p.exists():
            files.append(str(p))

    # 1) PRO 経由
    if files and hasattr(vbt, "ParquetData") and hasattr(vbt.ParquetData, "pull"):
        try:
            data = vbt.ParquetData.pull(paths=files, tz=tz)  # type: ignore[attr-defined]
            df = data.to_pd()
            df = _normalize_timeseries(df)
            if start is not None or end is not None:
                df = df.loc[start:end]
            df.columns = [str(c).lower() for c in df.columns]
            return df
        except Exception:
            # 下のフォールバックへ
            pass

    # 2) pandas フォールバック
    parts: list[pd.DataFrame] = []
    for sym in symbols:
        p = root / sym / tf / "ohlcv.parquet"
        if not p.exists():
            continue
        frame = pd.read_parquet(p)
        frame = _normalize_timeseries(frame)
        if start is not None or end is not None:
            frame = frame.loc[start:end]
        frame.columns = [str(c).lower() for c in frame.columns]
        parts.append(frame)

    if not parts:
        raise FileNotFoundError(
            f"No Parquet found under {root} for symbols={list(symbols)} timeframe={tf}"
        )

    if len(parts) == 1:
        return parts[0]

    # 簡易マルチシンボル結合（列階層: keys=symbols）
    return pd.concat(parts, axis=1, keys=list(symbols))


# ---- Backtest-related lazy bindings -------------------------------------------------


def _import_vbt():
    """vectorbtpro があれば優先、なければ vectorbt を返す。"""
    try:  # pragma: no cover - 実環境に依存
        vbt = importlib.import_module("vectorbtpro")
        return vbt, True
    except Exception:  # pragma: no cover - フォールバック
        vbt = importlib.import_module("vectorbt")
        return vbt, False


def make_ohlc_data(df: pd.DataFrame) -> Any:
    """
    vbt PRO: OHLCData へ変換。open/high/low/close 小文字列を前提。
    Fallback: DataFrame をそのまま返す。
    """
    vbt, is_pro = _import_vbt()
    if is_pro and hasattr(vbt, "OHLCData"):
        # 代表的な実装パターンを順に試す
        if hasattr(vbt.OHLCData, "from_df"):
            return vbt.OHLCData.from_df(df)  # type: ignore[attr-defined]
        if hasattr(vbt.OHLCData, "from_ohlc"):
            return vbt.OHLCData.from_ohlc(
                open=df["open"], high=df["high"], low=df["low"], close=df["close"]
            )
    return df


def _filter_pf_kwargs(vbt: Any, params: Mapping[str, Any] | None) -> dict[str, Any]:
    """vbt.Portfolio.from_signals が受け付ける引数のみ通す安全フィルタ。
    未知キー（例: session_preset）はここで除去する。
    """
    if not params:
        return {}
    try:
        sig = inspect.signature(vbt.Portfolio.from_signals)  # type: ignore[attr-defined]
        allowed = {
            name
            for name, p in sig.parameters.items()
            if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
        }
        return {k: v for k, v in dict(params).items() if k in allowed}
    except Exception:
        # 署名が取得できない場合は無難に既知の代表キーのみ許可
        whitelist = {
            "size",
            "fees",
            "slippage",
            "init_cash",
            "cash_sharing",
            "freq",
            "ts_index",
            "price",
            "direction",
            "sl_stop",
            "tp_stop",
            # 複数建て（ピラミディング）関連
            "accumulate",
            "max_entries",
            # トレーリング関連（対応環境のみ有効）
            "sl_trail",
        }
        return {k: v for k, v in dict(params).items() if k in whitelist}


def portfolio_from_signals(  # noqa: PLR0915
    price_like: Any,
    entries: pd.Series,
    exits: pd.Series,
    *,
    params: Mapping[str, Any] | None = None,
) -> Any:
    """
    vbt( PRO ) の Portfolio.from_signals を呼び出す薄いラッパ。
    - price='open' による「前バー判定→次足Open約定」の契約に合わせる前提
    - params には fees / slippage / size / stop 系を受け取る
    """
    vbt, _ = _import_vbt()
    debug_on = str(os.environ.get("GD_BT_DEBUG", "0")).strip().lower() in ("1", "true", "yes")
    # --- 正規化: 未知キー除去 + RR/ATR 変換 ---------------------------------
    p = dict(params or {})
    # vbtが知らない可能性のあるキーはここで処理 or 除去
    p.pop("session_preset", None)

    # 比率指定 / RR 指定 / ATR 指定を sl_stop/tp_stop に正規化
    sl_stop = p.pop("sl_stop", None)
    tp_stop = p.pop("tp_stop", None)
    sl_pct = p.pop("sl_pct", None)
    tp_pct = p.pop("tp_pct", None)
    rr = p.pop("rr", None)
    sl_atr_mult = p.pop("sl_atr_mult", None)
    tp_atr_mult = p.pop("tp_atr_mult", None)
    atr_window = int(p.pop("atr_window", 14))
    # 追加: time-based exit / trailing stop ブリッジ
    max_bars_hold = p.pop("max_bars_hold", None)
    sl_trail_flag = p.pop("sl_trail", None)

    def _to_df(obj: Any) -> pd.DataFrame | None:
        # OHLCData / PRO系は to_pd() or to_df() があるケースが多い
        for attr in ("to_pd", "to_df"):
            if hasattr(obj, attr):
                try:
                    df = getattr(obj, attr)()
                    if isinstance(df, pd.DataFrame):
                        return df
                except Exception:
                    pass
        if isinstance(obj, pd.DataFrame):
            return obj
        return None

    def _get_cols(df: pd.DataFrame, name: str) -> pd.DataFrame:
        if name in df.columns:
            return df[[name]]
        try:
            return df.xs(name, level=-1, axis=1)
        except Exception as e:  # pragma: no cover
            raise KeyError(f"Column '{name}' not found for ATR calc: {e}") from e

    def _calc_atr_rel(df: pd.DataFrame, window: int) -> pd.DataFrame:
        high = _get_cols(df, "high")
        low = _get_cols(df, "low")
        close = _get_cols(df, "close")
        prev_close = close.shift(1)
        tr = np.maximum(
            high.values - low.values,
            np.maximum((high.values - prev_close.values), (low.values - prev_close.values)),
        )
        tr_df = pd.DataFrame(tr, index=close.index, columns=close.columns)
        atr = tr_df.ewm(alpha=1.0 / float(window), adjust=False, min_periods=window).mean()
        # 相対（対 close）に変換
        rel = atr / close.replace(0, np.nan)
        return rel.fillna(0.0)

    # 1) pctベースを優先
    if sl_stop is None and sl_pct is not None:
        sl_stop = float(sl_pct)
    if tp_stop is None and tp_pct is not None:
        tp_stop = float(tp_pct)
    if tp_stop is None and rr is not None and sl_stop is not None:
        tp_stop = float(rr) * float(sl_stop)

    # 2) ATRベース（DFが取れる場合のみ）
    if (sl_atr_mult is not None or tp_atr_mult is not None) and (
        sl_stop is None or tp_stop is None
    ):
        df_price = _to_df(price_like)
        if df_price is not None:
            rel_atr = _calc_atr_rel(df_price, atr_window)
            if sl_stop is None and sl_atr_mult is not None:
                sl_stop = rel_atr * float(sl_atr_mult)
            if tp_stop is None and tp_atr_mult is not None:
                tp_stop = rel_atr * float(tp_atr_mult)
        # DFが取れなければATR指定は黙って無視（安全）

    # Time-based exit: entries から N 本後に強制 exit（簡易近似）
    if isinstance(max_bars_hold, int | float) and int(max_bars_hold) > 0:
        try:
            n = int(max_bars_hold)
            time_exit = entries.shift(n).astype(bool).fillna(False)
            exits = exits.astype(bool) | time_exit
        except Exception:
            # 失敗しても元の exits を使用
            pass

    # sl_trail は API 支持時のみ通すため、フィルタ前の params に戻す
    if isinstance(sl_trail_flag, bool):
        p["sl_trail"] = sl_trail_flag

    # ホワイトリスト抽出（from_signals の署名でフィルタ）
    kwargs = _filter_pf_kwargs(vbt, p)
    if sl_stop is not None:
        kwargs["sl_stop"] = sl_stop
    if tp_stop is not None:
        kwargs["tp_stop"] = tp_stop
    # sl_trail は _filter_pf_kwargs 内の署名判定でサポート非対応なら自動で落ちる

    # --- Debug dump ---------------------------------------------------------------
    if debug_on:
        try:
            dbg_dir = Path("runs/debug")
            dbg_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
            # 軽量統計
            meta = {
                "timestamp_utc": ts,
                "entries_true": int(pd.Series(entries).astype(bool).sum()),
                "exits_true": int(pd.Series(exits).astype(bool).sum()),
                "params_keys": sorted(list((params or {}).keys())),
                "kwargs_keys": sorted(list(kwargs.keys())),
                "has_sl_stop": sl_stop is not None,
                "has_tp_stop": tp_stop is not None,
            }
            (dbg_dir / f"meta_{ts}.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            # 明細（重い可能性があるため long_index は避ける）
            pd.DataFrame({"entries": pd.Series(entries).astype(bool)}).to_csv(
                dbg_dir / f"entries_{ts}.csv", index=True
            )
            pd.DataFrame({"exits": pd.Series(exits).astype(bool)}).to_csv(
                dbg_dir / f"exits_{ts}.csv", index=True
            )
            # stops はスカラー or DataFrame/Series の可能性
            if isinstance(sl_stop, pd.Series | pd.DataFrame | np.ndarray):
                pd.DataFrame(sl_stop).to_csv(dbg_dir / f"sl_stop_{ts}.csv")
            if isinstance(tp_stop, pd.Series | pd.DataFrame | np.ndarray):
                pd.DataFrame(tp_stop).to_csv(dbg_dir / f"tp_stop_{ts}.csv")
            # params/kwargsも保存
            (dbg_dir / f"params_{ts}.json").write_text(
                json.dumps(dict(params or {}), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (dbg_dir / f"kwargs_{ts}.json").write_text(
                json.dumps(kwargs, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            # デバッグ出力は本処理を阻害しない
            pass

    # 一般的な open-source vectorbt は `close=` 名だが、OHLCData でも受けられることがある
    if hasattr(vbt, "Portfolio"):
        try:
            return vbt.Portfolio.from_signals(  # type: ignore[attr-defined]
                close=price_like,
                entries=entries,
                exits=exits,
                price="open",
                **kwargs,
            )
        except TypeError:
            # フォールバック：引数名の差異を吸収（例：data= / ohlc= 等）
            for alt in ("data", "ohlc"):
                try:
                    return vbt.Portfolio.from_signals(  # type: ignore[attr-defined]
                        **{alt: price_like},
                        entries=entries,
                        exits=exits,
                        price="open",
                        **kwargs,
                    )
                except TypeError:
                    continue

    raise RuntimeError("vectorbt / vectorbtpro の Portfolio API が見つかりません")


def portfolio_metrics(portfolio: Any) -> dict[str, Any]:
    """
    Portfolio から汎用メトリクスを抽出（存在するものだけ拾う）。
    vbt PRO / vectorbt 両対応の薄ラッパ。
    """
    metrics: dict[str, Any] = {}

    def _get(obj: Any, name: str):
        if hasattr(obj, name):
            val = getattr(obj, name)
            try:
                return val() if callable(val) else val
            except Exception:
                return val
        return None

    stats = _get(portfolio, "stats")
    if stats is not None:
        try:
            metrics["stats"] = stats.to_dict() if hasattr(stats, "to_dict") else stats
        except Exception:
            metrics["stats"] = stats

    for k in ("total_return", "sharpe_ratio", "trades", "equity_curve"):
        v = _get(portfolio, k)
        if v is not None:
            metrics[k] = v

    # 補完: equity_curve が無い実装向けに value() を使用
    if "equity_curve" not in metrics:
        val = _get(portfolio, "value")
        try:
            if callable(val):
                val = val()
        except Exception:
            val = None
        if isinstance(val, pd.Series):
            metrics["equity_curve"] = val

    # 補完: total_return が無ければ equity_curve から計算
    if "total_return" not in metrics and isinstance(metrics.get("equity_curve"), pd.Series):
        eq = metrics["equity_curve"].astype(float)
        if len(eq) >= 2 and float(eq.iloc[0]) > 0.0:  # noqa: PLR2004
            metrics["total_return"] = float(eq.iloc[-1]) / float(eq.iloc[0]) - 1.0
        else:
            metrics["total_return"] = 0.0
    return metrics
