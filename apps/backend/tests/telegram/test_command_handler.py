import uuid
from datetime import UTC, datetime

from app.schemas.inventory_status import InventoryStatusResponse
from app.telegram.command_handler import TelegramCommandHandler
from app.telegram.status_formatter import InventoryStatusFormatter


class FakeInventoryStatusService:
    def __init__(
        self,
        statuses: list[InventoryStatusResponse],
    ) -> None:
        self._statuses = statuses

    def get_statuses(
        self,
    ) -> list[InventoryStatusResponse]:
        return self._statuses


def create_status(
    *,
    status: str = "low_stock",
    detected_units: int | None = 1,
    stock_percentage: float | None = 25.0,
) -> InventoryStatusResponse:
    return InventoryStatusResponse(
        configuration_id=uuid.uuid4(),
        camera_id=uuid.uuid4(),
        camera_name="Shelf Camera 01",
        product_id=uuid.uuid4(),
        product_name="Coca-Cola 500 ml",
        product_sku="COKE-500",
        detected_units=detected_units,
        shelf_capacity=4,
        stock_percentage=stock_percentage,
        low_stock_threshold=50.0,
        status=status,  # type: ignore[arg-type]
        detector_name=("opencv_roi" if detected_units is not None else None),
        captured_at=(datetime.now(UTC) if detected_units is not None else None),
    )


def test_status_command_returns_inventory_status() -> None:
    service = FakeInventoryStatusService(
        statuses=[
            create_status(),
        ],
    )

    handler = TelegramCommandHandler(
        inventory_status_service=service,  # type: ignore[arg-type]
        status_formatter=InventoryStatusFormatter(),
    )

    response = handler.handle("/status")

    assert "Coca-Cola 500 ml" in response
    assert "COKE-500" in response
    assert "Stock: 1/4 (25.00%)" in response
    assert "⚠️" in response


def test_status_command_supports_bot_username_suffix() -> None:
    service = FakeInventoryStatusService(
        statuses=[
            create_status(),
        ],
    )

    handler = TelegramCommandHandler(
        inventory_status_service=service,  # type: ignore[arg-type]
        status_formatter=InventoryStatusFormatter(),
    )

    response = handler.handle(
        "/status@ShelfStockMonitorBot",
    )

    assert "Coca-Cola 500 ml" in response


def test_status_command_returns_unknown_inventory() -> None:
    service = FakeInventoryStatusService(
        statuses=[
            create_status(
                status="unknown",
                detected_units=None,
                stock_percentage=None,
            ),
        ],
    )

    handler = TelegramCommandHandler(
        inventory_status_service=service,  # type: ignore[arg-type]
        status_formatter=InventoryStatusFormatter(),
    )

    response = handler.handle("/status")

    assert "Stock: unknown" in response
    assert "❓" in response


def test_status_command_handles_empty_inventory() -> None:
    service = FakeInventoryStatusService(
        statuses=[],
    )

    handler = TelegramCommandHandler(
        inventory_status_service=service,  # type: ignore[arg-type]
        status_formatter=InventoryStatusFormatter(),
    )

    response = handler.handle("/status")

    assert response == "📦 No active shelf configurations found."


def test_help_command_returns_available_commands() -> None:
    service = FakeInventoryStatusService(
        statuses=[],
    )

    handler = TelegramCommandHandler(
        inventory_status_service=service,  # type: ignore[arg-type]
        status_formatter=InventoryStatusFormatter(),
    )

    response = handler.handle("/help")

    assert "/status" in response
    assert "/help" in response


def test_unknown_command_returns_help_hint() -> None:
    service = FakeInventoryStatusService(
        statuses=[],
    )

    handler = TelegramCommandHandler(
        inventory_status_service=service,  # type: ignore[arg-type]
        status_formatter=InventoryStatusFormatter(),
    )

    response = handler.handle("/something")

    assert response == ("Unknown command.\nUse /help to see available commands.")
