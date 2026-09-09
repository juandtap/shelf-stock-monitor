from app.schemas.inventory_status import InventoryStatusResponse


class InventoryStatusFormatter:
    def format_statuses(
        self,
        statuses: list[InventoryStatusResponse],
    ) -> str:
        if not statuses:
            return "📦 No active shelf configurations found."

        sections = [self._format_status(status) for status in statuses]

        return "\n\n".join(sections)

    def _format_status(
        self,
        status: InventoryStatusResponse,
    ) -> str:
        if status.status == "unknown":
            return (
                f"❓ {status.product_name}\n"
                f"SKU: {status.product_sku}\n"
                f"Camera: {status.camera_name}\n"
                "Stock: unknown\n"
                f"Capacity: {status.shelf_capacity}"
            )

        status_icon = "⚠️" if status.status == "low_stock" else "✅"

        captured_at = (
            status.captured_at.isoformat() if status.captured_at is not None else "unknown"
        )

        return (
            f"{status_icon} {status.product_name}\n"
            f"SKU: {status.product_sku}\n"
            f"Camera: {status.camera_name}\n"
            f"Stock: {status.detected_units}/{status.shelf_capacity}"
            f" ({status.stock_percentage:.2f}%)\n"
            f"Threshold: {status.low_stock_threshold:.2f}%\n"
            f"Detector: {status.detector_name}\n"
            f"Captured: {captured_at}"
        )
