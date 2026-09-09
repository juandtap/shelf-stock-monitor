import asyncio
from collections.abc import Callable

import httpx
from loguru import logger
from sqlalchemy.orm import Session

from app.services.inventory_status import InventoryStatusService
from app.telegram.client import TelegramBotClient
from app.telegram.command_handler import TelegramCommandHandler
from app.telegram.models import TelegramUpdate
from app.telegram.status_formatter import InventoryStatusFormatter


class TelegramPollingService:
    def __init__(
        self,
        *,
        client: TelegramBotClient,
        session_factory: Callable[[], Session],
        allowed_chat_id: str,
    ) -> None:
        if not allowed_chat_id:
            raise ValueError(
                "Telegram chat ID is required.",
            )

        self._client = client
        self._session_factory = session_factory
        self._allowed_chat_id = allowed_chat_id
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is not None:
            return

        self._task = asyncio.create_task(
            self._run(),
            name="telegram-polling",
        )

        logger.info(
            "Telegram polling started",
        )

    async def shutdown(self) -> None:
        if self._task is not None:
            self._task.cancel()

            try:
                await self._task
            except asyncio.CancelledError:
                pass

            self._task = None

        await self._client.close()

        logger.info(
            "Telegram polling stopped",
        )

    async def _run(self) -> None:
        offset: int | None = None

        while True:
            try:
                updates = await self._client.get_updates(
                    offset=offset,
                )

                for update in updates:
                    offset = update.update_id + 1

                    await self._process_update(
                        update,
                    )

            except asyncio.CancelledError:
                raise
            except httpx.HTTPError as exc:
                logger.error(
                    "Telegram polling HTTP error | error={}",
                    exc,
                )

                await asyncio.sleep(2)
            except Exception:
                logger.exception(
                    "Unexpected Telegram polling error",
                )

                await asyncio.sleep(2)

    async def _process_update(
        self,
        update: TelegramUpdate,
    ) -> None:
        message = update.message

        if message is None or message.text is None:
            return

        chat_id = str(message.chat.id)

        if chat_id != self._allowed_chat_id:
            logger.warning(
                "Ignoring Telegram message from unauthorized chat | chat_id={}",
                chat_id,
            )
            return

        logger.info(
            "Telegram command received | chat_id={} | text={}",
            chat_id,
            message.text,
        )

        response_text = await asyncio.to_thread(
            self._handle_command,
            message.text,
        )

        await self._client.send_message(
            chat_id=message.chat.id,
            text=response_text,
        )

        logger.info(
            "Telegram message sent | chat_id={} | text={}",
            chat_id,
            response_text,
        )

    def _handle_command(
        self,
        text: str,
    ) -> str:
        db = self._session_factory()

        try:
            inventory_service = InventoryStatusService(
                db,
            )

            command_handler = TelegramCommandHandler(
                inventory_status_service=inventory_service,
                status_formatter=InventoryStatusFormatter(),
            )

            return command_handler.handle(
                text,
            )
        finally:
            db.close()
