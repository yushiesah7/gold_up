from __future__ import annotations

from enum import Enum
from pydantic import BaseModel


class DomainEventType(str, Enum):
    ORDER_PLACED = "OrderPlaced"
    STOP_UPDATED = "StopUpdated"
    POSITION_CLOSED = "PositionClosed"


class DomainEvent(BaseModel):
    type: DomainEventType
    payload: dict
