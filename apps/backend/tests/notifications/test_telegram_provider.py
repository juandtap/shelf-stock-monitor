import uuid
from unittest.mock import Mock, patch

from app.notifications.models import LowStockNotification
from app.notifications.telegram_provider import TelegramNotificationProvider


def create_notification() -> LowStockNotification:
    return LowStockNotification(
        alert_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        observation_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        product_name="Shampoo",
        camera_name="Shelf Camera 01",
        detected_units=1,
        shelf_capacity=4,
        stock_percentage=25.0,
        threshold_percentage=50.0,
        reason="significant_stock_drop",
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

    notification = create_notification()

    provider.send_low_stock_alert(notification)

    mock_post.assert_called_once()

    call = mock_post.call_args

    assert call.args[0] == ("https://api.telegram.org/bottest-token/sendMessage")

    payload = call.kwargs["json"]

    assert payload["chat_id"] == "123456789"

    message = payload["text"]

    assert "Shampoo" in message
    assert "Shelf Camera 01" in message
    assert "25.00%" in message
    assert "1/4 units" in message
    assert "50.00%" in message
    assert "Reason: Significant stock drop" in message

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
