"""Tests for YooMoney webhook handler."""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Set required env vars before importing app
os.environ.setdefault("YOOMONEY_RECEIVER_WALLET", "test_wallet")
os.environ.setdefault("YOOMONEY_NOTIFICATION_SECRET", "test_secret")

from src.core.config import settings
from src.webapp.main import app


@pytest.fixture(autouse=True)
def reset_settings():
    """Reset settings to known state before each test."""
    settings.yoomoney_access_token = ""
    settings.SUBSCRIPTION_TIERS = {30: 299, 90: 549, 180: 1199}
    settings.token_price = 49.0
    settings.yoomoney_notification_secret = "test_secret"
    settings.yoomoney_receiver_wallet = "test_wallet"


@pytest.fixture
def client():
    """FastAPI test client fixture."""
    return TestClient(app)


def test_webhook_invalid_hmac(client):
    """Returns 400 when HMAC validation fails."""
    with patch("src.webapp.main.validate_hmac", return_value=False):
        response = client.post(
            "/webhooks/yoomoney/notification",
            data={"amount": "100.00", "label": "12345_abc"},
        )

    assert response.status_code == 400


def test_webhook_test_notification(client):
    """Returns 200 ok for test notifications."""
    with patch("src.webapp.main.validate_hmac", return_value=True):
        response = client.post(
            "/webhooks/yoomoney/notification",
            data={"test_notification": "true"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_invalid_notification_type(client):
    """Returns 200 ok for unsupported notification types."""
    with patch("src.webapp.main.validate_hmac", return_value=True):
        response = client.post(
            "/webhooks/yoomoney/notification",
            data={
                "notification_type": "unknown-type",
                "label": "12345_abc",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_success(client):
    """Mock validate_hmac True, mock repository, verify 200 and calls."""
    subscription_mock = MagicMock()
    subscription_mock.expires_at = None
    subscription_mock.status = "active"

    with (
        patch("src.webapp.main.validate_hmac", return_value=True),
        patch(
            "src.webapp.main.repository.get_payment_by_operation_id",
            return_value=None,
        ),
        patch(
            "src.webapp.main.repository.update_payment_status",
        ) as mock_update,
        patch(
            "src.webapp.main.activate_subscription",
            return_value=subscription_mock,
        ) as mock_activate,
        patch("src.webapp.main.get_subscription_info", return_value={
            "is_active": True,
            "status": "active",
            "expires_at": None,
            "monthly_active": True,
            "tokens": 0,
            "last_payment_amount": None,
            "last_payment_date": None,
        }),
    ):
        response = client.post(
            "/webhooks/yoomoney/notification",
            data={
                "notification_type": "p2p-incoming",
                "operation_id": "op-123",
                "amount": "299.00",
                "label": "12345_monthly_30_abcdef",
            },
        )

    assert response.status_code == 200
    mock_activate.assert_called_once_with(12345, 299.0, "op-123", duration_days=30)
    mock_update.assert_called_once_with("12345_monthly_30_abcdef", "op-123", "completed")


def test_webhook_idempotency(client):
    """Already completed payment returns 200 without re-activating."""
    completed_payment = MagicMock()
    completed_payment.status = "completed"

    with (
        patch("src.webapp.main.validate_hmac", return_value=True),
        patch(
            "src.webapp.main.repository.get_payment_by_operation_id",
            return_value=completed_payment,
        ),
        patch(
            "src.webapp.main.activate_subscription",
        ) as mock_activate,
    ):
        response = client.post(
            "/webhooks/yoomoney/notification",
            data={
                "notification_type": "p2p-incoming",
                "operation_id": "op-123",
                "amount": "299.00",
                "label": "12345_monthly_30_abcdef",
            },
        )

    assert response.status_code == 200
    mock_activate.assert_not_called()
    assert response.json() == {"status": "ok"}


def test_webhook_amount_below_price(client):
    """Returns 400 when payment amount is below expected subscription price."""
    with (
        patch("src.webapp.main.validate_hmac", return_value=True),
        patch(
            "src.webapp.main.repository.get_payment_by_operation_id",
            return_value=None,
        ),
    ):
        response = client.post(
            "/webhooks/yoomoney/notification",
            data={
                "notification_type": "p2p-incoming",
                "operation_id": "op-123",
                "amount": "1.00",
                "label": "12345_monthly_30_abcdef",
            },
        )

    assert response.status_code == 400


def test_webhook_sends_notification_with_bot(client):
    """Sends activation notification to user when bot is available."""
    import asyncio

    mock_bot = MagicMock()
    mock_bot.send_message = MagicMock(return_value=asyncio.Future())
    mock_bot.send_message.return_value.set_result(None)
    app.state.bot = mock_bot

    subscription_mock = MagicMock()
    subscription_mock.expires_at = None
    subscription_mock.status = "active"

    with (
        patch("src.webapp.main.validate_hmac", return_value=True),
        patch(
            "src.webapp.main.repository.get_payment_by_operation_id",
            return_value=None,
        ),
        patch("src.webapp.main.repository.update_payment_status"),
        patch("src.webapp.main.activate_subscription", return_value=subscription_mock),
        patch("src.webapp.main.get_subscription_info", return_value={
            "is_active": True,
            "status": "active",
            "expires_at": None,
            "monthly_active": True,
            "tokens": 0,
            "last_payment_amount": None,
            "last_payment_date": None,
        }),
    ):
        response = client.post(
            "/webhooks/yoomoney/notification",
            data={
                "notification_type": "p2p-incoming",
                "operation_id": "op-123",
                "amount": "299.00",
                "label": "12345_monthly_30_abcdef",
            },
        )

    assert response.status_code == 200
    # The notification is sent via asyncio.create_task, give it a moment
    import time
    time.sleep(0.1)
    mock_bot.send_message.assert_called_once()
    call_args = mock_bot.send_message.call_args
    assert call_args[0][0] == 12345  # telegram_id
    assert "✅" in call_args[0][1]

    # Cleanup
    del app.state.bot


def test_webhook_no_notification_without_bot(client):
    """Does not crash when bot is not set on app.state."""
    if hasattr(app.state, "bot"):
        del app.state.bot

    subscription_mock = MagicMock()
    subscription_mock.expires_at = None
    subscription_mock.status = "active"

    with (
        patch("src.webapp.main.validate_hmac", return_value=True),
        patch(
            "src.webapp.main.repository.get_payment_by_operation_id",
            return_value=None,
        ),
        patch("src.webapp.main.repository.update_payment_status"),
        patch("src.webapp.main.activate_subscription", return_value=subscription_mock),
        patch("src.webapp.main.get_subscription_info", return_value={
            "is_active": True,
            "status": "active",
            "expires_at": None,
            "monthly_active": True,
            "tokens": 0,
            "last_payment_amount": None,
            "last_payment_date": None,
        }),
    ):
        response = client.post(
            "/webhooks/yoomoney/notification",
            data={
                "notification_type": "p2p-incoming",
                "operation_id": "op-123",
                "amount": "299.00",
                "label": "12345_monthly_30_abcdef",
            },
        )

    assert response.status_code == 200
