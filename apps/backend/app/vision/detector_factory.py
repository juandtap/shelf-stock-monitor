from typing import Protocol

from app.db.models.shelf_configuration import ShelfConfiguration
from app.vision.detector import StockDetector


class StockDetectorFactoryProtocol(Protocol):
    def create(
        self,
        configuration: ShelfConfiguration,
    ) -> StockDetector: ...
