from sqlalchemy.orm import Session

from app.telegram.models import (
    TelegramChat,
    TelegramMessage,
    TelegramUpdate,
)
from app.telegram.polling_service import TelegramPollingService


class FakeTelegramClient:
    def __init__(self) -> None:
        self.sent_messages: list[tuple[int, str]] = []

    async def send_message(
        self,
        *,
        chat_id: int,
        text: str,
    ) -> None:
        self.sent_messages.append(
            (
                chat_id,
                text,
            )
        )

    async def close(self) -> None:
        pass


def test_polling_service_ignores_unauthorized_chat(
    db_session: Session,
) -> None:
    client = FakeTelegramClient()

    def session_factory() -> Session:
        return db_session

    service = TelegramPollingService(
        client=client,  # type: ignore[arg-type]
        session_factory=session_factory,
        allowed_chat_id="12345",
    )

    update = TelegramUpdate(
        update_id=1,
        message=TelegramMessage(
            chat=TelegramChat(
                id=99999,
            ),
            text="/status",
        ),
    )

    import asyncio

    asyncio.run(
        service._process_update(update),  # noqa: SLF001
    )

    assert client.sent_messages == []
