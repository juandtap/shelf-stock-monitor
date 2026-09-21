import pytest

from app.vision.shelf_geometry import (
    SYNTHETIC_SHELF_SLOTS,
    ShelfSlot,
)


def test_synthetic_shelf_has_eight_slots() -> None:
    assert len(SYNTHETIC_SHELF_SLOTS) == 8


def test_shelf_slot_calculates_dimensions() -> None:
    slot = ShelfSlot(
        x1=10,
        y1=20,
        x2=110,
        y2=220,
    )

    assert slot.width == 100
    assert slot.height == 200


def test_shelf_slot_converts_to_region_of_interest() -> None:
    slot = ShelfSlot(
        x1=10,
        y1=20,
        x2=110,
        y2=220,
    )

    region = slot.to_region_of_interest()

    assert region.x == 10
    assert region.y == 20
    assert region.width == 100
    assert region.height == 200


@pytest.mark.parametrize(
    (
        "x1",
        "y1",
        "x2",
        "y2",
    ),
    [
        (-1, 0, 100, 100),
        (0, -1, 100, 100),
        (100, 0, 100, 100),
        (101, 0, 100, 100),
        (0, 100, 100, 100),
        (0, 101, 100, 100),
    ],
)
def test_shelf_slot_rejects_invalid_coordinates(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
) -> None:
    with pytest.raises(ValueError):
        ShelfSlot(
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
        )
