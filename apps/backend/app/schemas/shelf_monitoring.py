from pydantic import BaseModel, Field


class ShelfMonitoringRequest(BaseModel):
    image_path: str = Field(
        min_length=1,
        max_length=500,
    )
