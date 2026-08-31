from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from app.vision.models import StockDetectionResult

ImageArray = NDArray[np.uint8]


class StockDetector(Protocol):
    @property
    def name(self) -> str: ...

    def detect(self, image: ImageArray) -> StockDetectionResult: ...
