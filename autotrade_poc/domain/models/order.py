from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel

from .market import Symbol


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class Price(BaseModel):
    value: float  # 絶対価格（ブローカー桁は broker_specs で扱う）


class OrderId(BaseModel):
    value: int


class PositionId(BaseModel):
    value: int


class OrderRequest(BaseModel):
    symbol: Symbol
    side: OrderSide
    order_type: OrderType
    volume: float  # ロット
    price: Optional[Price] = None  # MARKET以外で使用
    sl: Optional[Price] = None
    tp: Optional[Price] = None
    client_tag: str | None = None  # magic or comment 等の識別用


class OrderResult(BaseModel):
    success: bool
    order_id: OrderId | None = None
    position_id: PositionId | None = None
    message: str | None = None  # ブローカー返却メッセージ/エラーコードの文字列表現


class ModifyResult(BaseModel):
    success: bool
    order_id: OrderId | None = None
    message: str | None = None


class CloseResult(BaseModel):
    success: bool
    position_id: PositionId | None = None
    closed_volume: float | None = None
    message: str | None = None


class Bar(BaseModel):
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
