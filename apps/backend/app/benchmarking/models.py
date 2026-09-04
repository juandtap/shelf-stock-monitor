from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BenchmarkSample:
    filename: str
    expected_units: int
    shelf_capacity: int

    def __post_init__(self) -> None:
        if self.expected_units < 0:
            raise ValueError("expected_units cannot be negative.")

        if self.shelf_capacity <= 0:
            raise ValueError("shelf_capacity must be positive.")

        if self.expected_units > self.shelf_capacity:
            raise ValueError("expected_units cannot be greater than shelf_capacity.")

    @property
    def expected_stock_percentage(self) -> float:
        return (self.expected_units / self.shelf_capacity) * 100.0


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    filename: str
    detector_name: str
    expected_units: int
    detected_units: int
    shelf_capacity: int
    expected_stock_percentage: float
    detected_stock_percentage: float
    absolute_units_error: int
    absolute_stock_percentage_error: float
    latency_ms: float


@dataclass(frozen=True, slots=True)
class BenchmarkSummary:
    detector_name: str
    sample_count: int
    units_mae: float
    stock_percentage_mae: float
    latency_mean_ms: float
    latency_p50_ms: float
    latency_p95_ms: float
