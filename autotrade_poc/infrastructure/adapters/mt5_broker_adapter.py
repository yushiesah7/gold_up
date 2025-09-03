from __future__ import annotations

from typing import Any, Sequence

import MetaTrader5 as mt5  # type: ignore

from autotrade_poc.ports.broker_port import BrokerPort, BrokerCredentials
from autotrade_poc.domain.models.order import OrderRequest, OrderResult, ModifyResult, CloseResult, PositionId
from autotrade_poc.domain.models.market import Symbol


class MT5BrokerAdapter(BrokerPort):
    """MetaTrader5 Python API 実装。
    - initialize/login/shutdown は外部のライフサイクルで管理する場合が多いが、
      ここでは connect() で initialize→login の最小実装を行い、
      アプリ終了時の shutdown は呼び出し側で責任を持つ（Runner等）。
    - 例外は ValueError/RuntimeError として投げる。UseCase 側で捕捉し Logger へ。
    """

    def __init__(self, *, default_deviation: int = 20, default_filling: int | None = None) -> None:
        self.default_deviation = default_deviation
        self.default_filling = default_filling  # None の場合はターミナル既定

    def connect(self, creds: BrokerCredentials) -> None:
        # 1) ターミナルへ attach
        if not mt5.initialize():
            raise RuntimeError(f"MT5.initialize failed: code={mt5.last_error()}")
        # 2) ログイン
        ok = mt5.login(
            login=int(creds.login),
            password=str(creds.password),
            server=str(creds.server),
        )
        if not ok:
            code = mt5.last_error()
            raise RuntimeError(f"MT5.login failed: code={code}")

    def place_order(self, req: OrderRequest) -> OrderResult:
        symbol = req.symbol.value
        # 市場情報が未ロードの場合に備えて select
        mt5.symbol_select(symbol, True)

        # サイド/タイプのマッピング（Marketのみ最小実装）
        if req.order_type.value == "market":
            action = mt5.TRADE_ACTION_DEAL
            if req.side.value == "buy":
                order_type = mt5.ORDER_TYPE_BUY
            else:
                order_type = mt5.ORDER_TYPE_SELL
        else:
            return OrderResult(success=False, message="Only market orders are supported in POC")

        request: dict[str, Any] = {
            "action": action,
            "symbol": symbol,
            "type": order_type,
            "volume": float(req.volume),
            # deviation は価格乖離許容。POCでは固定値/引数指定
            "deviation": int(self.default_deviation),
            # position/by position_id は新規なので不要
            # filling は口座依存。既定が合わない口座では default_filling 指定を推奨
        }
        if req.sl is not None:
            request["sl"] = float(req.sl.value)
        if req.tp is not None:
            request["tp"] = float(req.tp.value)
        if req.client_tag:
            request["comment"] = req.client_tag
        if self.default_filling is not None:
            request["type_filling"] = int(self.default_filling)

        result = mt5.order_send(request)
        if result is None:
            return OrderResult(success=False, message=f"order_send returned None: {mt5.last_error()}")

        if result.retcode == mt5.TRADE_RETCODE_DONE:
            return OrderResult(
                success=True,
                order_id=None if result.order == 0 else None,  # MT5は成行では position 優先
                position_id=PositionId(value=int(result.position)) if result.position else None,
                message=str(result),
            )
        else:
            return OrderResult(success=False, message=f"retcode={result.retcode}; {result}")

    def modify_stops(self, position_id: PositionId, *, sl: float | None, tp: float | None) -> ModifyResult:
        # MT5 は TRADE_ACTION_SLTP で SL/TP 更新
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": int(position_id.value),
        }
        if sl is not None:
            request["sl"] = float(sl)
        if tp is not None:
            request["tp"] = float(tp)

        result = mt5.order_send(request)
        if result is None:
            return ModifyResult(success=False, message=f"order_send(None): {mt5.last_error()}")
        ok = result.retcode == mt5.TRADE_RETCODE_DONE
        return ModifyResult(success=ok, order_id=None if not ok else None, message=str(result))

    def close_position(self, position_id: PositionId, *, volume: float | None = None) -> CloseResult:
        # 反対売買でクローズ（position 情報から種別を決定）
        pos_list = mt5.positions_get(ticket=int(position_id.value))
        if not pos_list:
            return CloseResult(success=False, position_id=None, closed_volume=None, message="position not found")
        pos = pos_list[0]
        symbol = pos.symbol
        vol = float(volume) if volume is not None else float(pos.volume)
        side = pos.type  # 0=BUY,1=SELL
        order_type = mt5.ORDER_TYPE_SELL if side == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "type": order_type,
            "position": int(position_id.value),
            "volume": vol,
            "deviation": self.default_deviation,
        }
        result = mt5.order_send(request)
        if result is None:
            return CloseResult(success=False, position_id=None, closed_volume=None, message=str(mt5.last_error()))
        ok = result.retcode == mt5.TRADE_RETCODE_DONE
        return CloseResult(
            success=ok, position_id=position_id if ok else None, closed_volume=vol if ok else None, message=str(result)
        )

    def positions(self, symbol: Symbol | None = None) -> Sequence[dict]:
        if symbol is None:
            data = mt5.positions_get()
        else:
            data = mt5.positions_get(symbol=symbol.value)
        if data is None:
            return []
        out: list[dict[str, Any]] = []
        for p in data:
            out.append(
                {
                    "ticket": int(p.ticket),
                    "symbol": str(p.symbol),
                    "type": int(p.type),  # 0=BUY,1=SELL
                    "volume": float(p.volume),
                    "price_open": float(p.price_open),
                    "sl": float(p.sl),
                    "tp": float(p.tp),
                    "profit": float(p.profit),
                }
            )
        return out
