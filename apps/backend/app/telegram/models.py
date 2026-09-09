from pydantic import BaseModel


class TelegramChat(BaseModel):
    id: int


class TelegramMessage(BaseModel):
    chat: TelegramChat
    text: str | None = None


class TelegramUpdate(BaseModel):
    update_id: int
    message: TelegramMessage | None = None


class TelegramUpdatesResponse(BaseModel):
    ok: bool
    result: list[TelegramUpdate]
