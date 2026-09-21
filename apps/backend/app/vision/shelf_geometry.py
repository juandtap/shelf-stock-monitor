from dataclasses import dataclass

from app.vision.models import RegionOfInterest


@dataclass(frozen=True)
class ShelfSlot:
    x1: int
    y1: int
    x2: int
    y2: int

    def __post_init__(self) -> None:
        if self.x1 < 0 or self.y1 < 0:
            raise ValueError("Shelf slot coordinates cannot be negative.")

        if self.x2 <= self.x1:
            raise ValueError("Shelf slot x2 must be greater than x1.")

        if self.y2 <= self.y1:
            raise ValueError("Shelf slot y2 must be greater than y1.")

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    def to_region_of_interest(
        self,
    ) -> RegionOfInterest:
        return RegionOfInterest(
            x=self.x1,
            y=self.y1,
            width=self.width,
            height=self.height,
        )


SYNTHETIC_SHELF_SLOTS = (
    ShelfSlot(135, 100, 495, 385),
    ShelfSlot(535, 100, 860, 385),
    ShelfSlot(870, 100, 1235, 385),
    ShelfSlot(1240, 100, 1590, 385),
    ShelfSlot(135, 460, 495, 685),
    ShelfSlot(535, 460, 860, 685),
    ShelfSlot(870, 460, 1235, 685),
    ShelfSlot(1240, 460, 1590, 685),
)
