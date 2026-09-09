import httpx

from app.telegram.models import (
    TelegramUpdate,
    TelegramUpdatesResponse,
)


class TelegramBotClient:
    API_BASE_URL = "https://api.telegram.org"

    def __init__(
        self,
        *,
        bot_token: str,
        request_timeout_seconds: float,
        polling_timeout_seconds: int,
    ) -> None:
        if not bot_token:
            raise ValueError(
                "Telegram bot token is required.",
            )

        self._base_url = f"{self.API_BASE_URL}/bot{bot_token}"
        self._polling_timeout_seconds = polling_timeout_seconds

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                request_timeout_seconds + polling_timeout_seconds,
            ),
        )

    async def get_updates(
        self,
        *,
        offset: int | None,
    ) -> list[TelegramUpdate]:
        payload: dict[str, object] = {
            "timeout": self._polling_timeout_seconds,
            "allowed_updates": [
                "message",
            ],
        }

        if offset is not None:
            payload["offset"] = offset

        response = await self._client.post(
            f"{self._base_url}/getUpdates",
            json=payload,
        )

        response.raise_for_status()

        telegram_response = TelegramUpdatesResponse.model_validate(
            response.json(),
        )

        if not telegram_response.ok:
            raise RuntimeError(
                "Telegram getUpdates returned an unsuccessful response.",
            )

        return telegram_response.result

    async def send_message(
        self,
        *,
        chat_id: int,
        text: str,
    ) -> None:
        response = await self._client.post(
            f"{self._base_url}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
            },
        )

        response.raise_for_status()

    async def close(self) -> None:
        await self._client.aclose()
