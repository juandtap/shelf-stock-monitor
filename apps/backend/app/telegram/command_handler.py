from app.services.inventory_status import InventoryStatusService
from app.telegram.status_formatter import InventoryStatusFormatter


class TelegramCommandHandler:
    def __init__(
        self,
        inventory_status_service: InventoryStatusService,
        status_formatter: InventoryStatusFormatter,
    ) -> None:
        self._inventory_status_service = inventory_status_service
        self._status_formatter = status_formatter

    def handle(
        self,
        text: str,
    ) -> str:
        command = self._normalize_command(text)

        if command == "/status":
            statuses = self._inventory_status_service.get_statuses()
            return self._status_formatter.format_statuses(statuses)

        if command == "/help":
            return self._help_message()

        return "Unknown command.\nUse /help to see available commands."

    @staticmethod
    def _normalize_command(
        text: str,
    ) -> str:
        stripped_text = text.strip()

        if not stripped_text:
            return ""

        command = stripped_text.split(maxsplit=1)[0]

        return command.split("@", maxsplit=1)[0].lower()

    @staticmethod
    def _help_message() -> str:
        return (
            "Shelf Stock Monitor\n\n"
            "/status - Show current inventory status\n"
            "/help - Show available commands"
        )
