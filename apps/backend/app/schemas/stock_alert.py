import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StockAlertResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: uuid.UUID
    stock_observation_id: uuid.UUID
    stock_percentage: float
    threshold_percentage: float
    created_at: datetime
    updated_at: datetime
