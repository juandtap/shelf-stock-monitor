from dataclasses import dataclass, field


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
class ClassDetection:
    class_id: int
    detected_units: int

    def __post_init__(self) -> None:
        if self.class_id < 0:
            raise ValueError("class_id cannot be negative.")

        if self.detected_units <= 0:
            raise ValueError("detected_units must be positive.")


@dataclass(frozen=True)
class StockDetectionResult:
    detected_units: int
    detector_name: str
    class_detections: tuple[ClassDetection, ...] = field(
        default_factory=tuple,
    )

    def __post_init__(self) -> None:
        if self.detected_units < 0:
            raise ValueError("detected_units cannot be negative.")

        if not self.detector_name:
            raise ValueError("detector_name cannot be empty.")

        class_total = sum(detection.detected_units for detection in self.class_detections)

        if self.class_detections and class_total != self.detected_units:
            raise ValueError(
                "Sum of class detections must match detected_units.",
            )
