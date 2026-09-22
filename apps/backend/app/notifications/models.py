import uuid
from dataclasses import dataclass

from app.db.models.stock_alert import StockAlertReason


@dataclass(frozen=True, slots=True)
class LowStockNotification:
    alert_id: uuid.UUID
    observation_id: uuid.UUID

    product_name: str
    camera_name: str

    detected_units: int
    shelf_capacity: int
    stock_percentage: float
    threshold_percentage: float
    reason: StockAlertReason
