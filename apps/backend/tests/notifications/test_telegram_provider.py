import uuid
from unittest.mock import Mock, patch

from app.db.models.stock_alert import StockAlert
from app.notifications.telegram_provider import TelegramNotificationProvider


def create_alert() -> StockAlert:
    return StockAlert(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        stock_observation_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        stock_percentage=25.0,
        threshold_percentage=50.0,
    )


@patch("app.notifications.telegram_provider.httpx.post")
def test_sends_low_stock_alert(
    mock_post: Mock,
) -> None:
    response = Mock()
    mock_post.return_value = response

    provider = TelegramNotificationProvider(
        bot_token="test-token",
        chat_id="123456789",
        timeout_seconds=10.0,
    )

    alert = create_alert()

    provider.send_low_stock_alert(alert)

    mock_post.assert_called_once()

    call = mock_post.call_args

    assert call.args[0] == "https://api.telegram.org/bottest-token/sendMessage"

    assert call.kwargs["json"]["chat_id"] == "123456789"
    assert "25.00%" in call.kwargs["json"]["text"]
    assert "50.00%" in call.kwargs["json"]["text"]
    assert call.kwargs["timeout"] == 10.0

    response.raise_for_status.assert_called_once_with()


def test_requires_bot_token() -> None:
    try:
        TelegramNotificationProvider(
            bot_token="",
            chat_id="123456789",
            timeout_seconds=10.0,
        )
    except ValueError as exc:
        assert "bot token" in str(exc).lower()
    else:
        raise AssertionError("Expected ValueError.")


def test_requires_chat_id() -> None:
    try:
        TelegramNotificationProvider(
            bot_token="test-token",
            chat_id="",
            timeout_seconds=10.0,
        )
    except ValueError as exc:
        assert "chat id" in str(exc).lower()
    else:
        raise AssertionError("Expected ValueError.")
