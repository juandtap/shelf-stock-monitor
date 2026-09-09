from dataclasses import dataclass


@dataclass(frozen=True)
class RegionOfInterest:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.x < 0 or self.y < 0:
            raise ValueError("ROI coordinates cannot be negative.")

        if self.width <= 0 or self.height <= 0:
            raise ValueError("ROI dimensions must be positive.")


@dataclass(frozen=True)
class StockDetectionResult:
    detected_units: int
    detector_name: str
