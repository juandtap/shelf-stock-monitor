import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

InventoryState = Literal[
    "ok",
    "low_stock",
    "unknown",
]


class InventoryStatusResponse(BaseModel):
    configuration_id: uuid.UUID

    camera_id: uuid.UUID
    camera_name: str

    product_id: uuid.UUID
    product_name: str
    product_sku: str

    detected_units: int | None
    shelf_capacity: int
    stock_percentage: float | None

    low_stock_threshold: float
    status: InventoryState

    detector_name: str | None
    captured_at: datetime | None
