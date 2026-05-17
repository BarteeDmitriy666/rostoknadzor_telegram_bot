"""Tests for subscription service."""

from datetime import UTC, datetime, timedelta

import pytest
from peewee import SqliteDatabase

from src.db.models import Payment, Subscription


@pytest.fixture
def setup_db():
    """Set up in-memory SQLite with Subscription and Payment tables."""
    from src.db import models

    test_db = SqliteDatabase(":memory:")
    original_db = models.database

    models.database = test_db
    Subscription._meta.database = test_db
    Payment._meta.database = test_db

    test_db.create_tables([Subscription, Payment], safe=True)

    yield test_db

    test_db.drop_tables([Subscription, Payment], safe=True)
    test_db.close()
    models.database = original_db


def test_is_subscribed_no_subscription(setup_db):
    """Returns False when no subscription exists."""
    from src.payments.subscription import is_subscribed

    assert is_subscribed(12345) is False


def test_is_subscribed_active(setup_db):
    """Returns True for active subscription."""
    from src.payments.repository import upsert_subscription
    from src.payments.subscription import is_subscribed

    future = datetime.now(UTC) + timedelta(days=30)
    upsert_subscription(12345, "active", future, "tx-1")

    assert is_subscribed(12345) is True


def test_is_subscribed_expired(setup_db):
    """Returns False and marks inactive for expired subscription."""
    from src.payments.repository import get_subscription, upsert_subscription
    from src.payments.subscription import is_subscribed

    past = datetime.now(UTC) - timedelta(days=1)
    upsert_subscription(12345, "active", past, "tx-1")

    assert is_subscribed(12345) is False

    sub = get_subscription(12345)
    assert sub.status == "inactive"


def test_is_subscribed_lifetime(setup_db):
    """Returns True for lifetime subscription (expires_at=None)."""
    from src.payments.repository import upsert_subscription
    from src.payments.subscription import is_subscribed

    upsert_subscription(12345, "active", None, "tx-1")

    assert is_subscribed(12345) is True


def test_activate_subscription_creates_new(setup_db):
    """Activates new subscription."""
    from src.payments.subscription import activate_subscription

    sub = activate_subscription(12345, 199.0, "op-1", 30)

    assert sub.telegram_id == 12345
    assert sub.status == "active"
    assert sub.expires_at is not None
    assert sub.transaction_id == "op-1"


def test_activate_subscription_updates_existing(setup_db):
    """Updates existing subscription."""
    from src.payments.repository import upsert_subscription
    from src.payments.subscription import activate_subscription

    past = datetime.now(UTC) - timedelta(days=30)
    upsert_subscription(12345, "active", past, "old-tx")

    sub = activate_subscription(12345, 199.0, "new-op", 30)

    assert sub.transaction_id == "new-op"
    assert sub.expires_at > past


def test_activate_subscription_lifetime(setup_db):
    """duration_days=0 sets expires_at=None."""
    from src.payments.subscription import activate_subscription

    sub = activate_subscription(12345, 199.0, "op-1", 0)

    assert sub.expires_at is None


def test_activate_subscription_extends_active(setup_db):
    """Renewal extends from current expires_at, not from now."""
    from src.payments.repository import get_subscription, upsert_subscription
    from src.payments.subscription import activate_subscription

    from datetime import UTC, datetime, timedelta

    future = datetime.now(UTC) + timedelta(days=25)
    upsert_subscription(12345, "active", future, "old-tx")

    sub = activate_subscription(12345, 199.0, "new-op", 30)

    # Should extend from the existing expiration, not from now
    # So expires_at should be ~55 days from now (25 remaining + 30 new), not ~30
    assert sub.expires_at > datetime.now(UTC) + timedelta(days=50)
    assert sub.expires_at < datetime.now(UTC) + timedelta(days=60)


def test_get_subscription_info(setup_db):
    """Returns correct dict with status, is_active, last_payment info."""
    from src.payments.repository import create_payment, update_payment_status
    from src.payments.subscription import activate_subscription, get_subscription_info

    activate_subscription(12345, 199.0, "op-1", 30)
    create_payment(12345, 199.0, "label-1")
    update_payment_status("label-1", "op-1", "completed")

    info = get_subscription_info(12345)

    assert info["status"] == "active"
    assert info["is_active"] is True
    assert info["monthly_active"] is True
    assert info["tokens"] == 0
    assert info["expires_at"] is not None
    assert info["last_payment_amount"] == 199.0
    assert info["last_payment_date"] is not None


def test_get_last_payment_ignores_pending(setup_db):
    """get_last_payment only returns completed payments."""
    from src.payments.repository import create_payment, get_last_payment, update_payment_status

    # Create a pending payment, then a completed one
    create_payment(12345, 199.0, "label-pending")
    create_payment(12345, 199.0, "label-completed")
    update_payment_status("label-completed", "op-1", "completed")

    last = get_last_payment(12345)
    assert last is not None
    assert last.label == "label-completed"
    assert last.status == "completed"


def test_get_last_payment_returns_none_when_only_pending(setup_db):
    """get_last_payment returns None if user only has pending payments."""
    from src.payments.repository import create_payment, get_last_payment

    create_payment(12345, 199.0, "label-pending")

    assert get_last_payment(12345) is None


def test_get_pending_payment_returns_earliest_pending(setup_db):
    """get_pending_payment returns the most recent pending payment."""
    from src.payments.repository import create_payment, get_pending_payment

    create_payment(12345, 199.0, "label-1")
    create_payment(12345, 199.0, "label-2")

    pending = get_pending_payment(12345)
    assert pending is not None
    assert pending.status == "pending"
    assert pending.label == "label-2"  # Most recent


def test_get_pending_payment_returns_none_when_completed(setup_db):
    """get_pending_payment returns None if user has no pending payments."""
    from src.payments.repository import create_payment, get_pending_payment, update_payment_status

    create_payment(12345, 199.0, "label-1")
    update_payment_status("label-1", "op-1", "completed")

    assert get_pending_payment(12345) is None


def test_is_subscribed_with_tokens(setup_db):
    """Returns True when user has tokens even without monthly sub."""
    from src.payments.repository import upsert_subscription
    from src.payments.subscription import is_subscribed

    upsert_subscription(12345, "inactive", None, "tx-1", tokens=5)

    assert is_subscribed(12345) is True


def test_is_subscribed_monthly_priority_over_tokens(setup_db):
    """Monthly sub has priority — is_subscribed returns True for monthly even with 0 tokens."""
    from src.payments.repository import upsert_subscription
    from src.payments.subscription import is_subscribed

    future = datetime.now(UTC) + timedelta(days=30)
    upsert_subscription(12345, "active", future, "tx-1", tokens=0)

    assert is_subscribed(12345) is True


def test_add_tokens(setup_db):
    """add_tokens increments token count on existing subscription."""
    from src.payments.repository import get_subscription, upsert_subscription
    from src.payments.subscription import add_tokens

    upsert_subscription(12345, "inactive", None, "tx-1", tokens=3)
    sub = add_tokens(12345, 5)

    assert sub.tokens == 8


def test_add_tokens_creates_subscription(setup_db):
    """add_tokens creates subscription if none exists."""
    from src.payments.subscription import add_tokens

    sub = add_tokens(99999, 10)

    assert sub.tokens == 10


def test_consume_token(setup_db):
    """consume_token decrements token count when monthly sub is not active."""
    from src.payments.repository import upsert_subscription
    from src.payments.subscription import consume_token

    upsert_subscription(12345, "inactive", None, "tx-1", tokens=5)
    sub = consume_token(12345)

    assert sub is not None
    assert sub.tokens == 4


def test_consume_token_no_tokens(setup_db):
    """consume_token returns None when no tokens available."""
    from src.payments.repository import upsert_subscription
    from src.payments.subscription import consume_token

    upsert_subscription(12345, "inactive", None, "tx-1", tokens=0)

    assert consume_token(12345) is None


def test_consume_token_monthly_active_no_consumption(setup_db):
    """consume_token does not consume when monthly sub is active."""
    from src.payments.repository import upsert_subscription
    from src.payments.subscription import consume_token

    future = datetime.now(UTC) + timedelta(days=30)
    upsert_subscription(12345, "active", future, "tx-1", tokens=5)
    sub = consume_token(12345)

    assert sub is not None
    assert sub.tokens == 5  # Not consumed


def test_activate_subscription_preserves_tokens(setup_db):
    """Activating monthly sub preserves existing tokens."""
    from src.payments.repository import upsert_subscription
    from src.payments.subscription import activate_subscription

    upsert_subscription(12345, "inactive", None, "tx-1", tokens=10)
    sub = activate_subscription(12345, 199.0, "op-1", 30)

    assert sub.status == "active"
    assert sub.tokens == 10
