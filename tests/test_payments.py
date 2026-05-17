"""Tests for YooMoney payment utilities."""

import hashlib
import hmac
import urllib.parse
from unittest.mock import MagicMock, patch

import pytest

from src.payments.yoomoney import (
    create_payment_link,
    parse_label,
    validate_hmac,
    verify_payment_wallet_api,
)


def test_create_payment_link_format():
    """Verify URL contains receiver, sum, label with correct format."""
    url, label = create_payment_link(12345, 199.0, "4100112345678")

    assert "4100112345678" in url
    assert "199.00" in url
    assert label.startswith("12345_monthly_0_")
    parts = label.split("_")
    assert int(parts[0]) == 12345
    assert parts[1] == "monthly"
    assert parts[2] == "0"
    hex_part = parts[3]
    assert len(hex_part) == 16


def test_validate_hmac_success():
    """Test HMAC validation with known good params and secret."""
    secret = "my_secret"
    params = {
        "amount": "199.00",
        "currency": "RUB",
        "label": "12345678_deadbeef",
    }

    # Compute expected sign manually
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    concat = "&".join(
        f"{k}={urllib.parse.quote(v, safe='')}" for k, v in sorted_params
    )
    expected_sign = (
        hmac.new(
            secret.encode("utf-8"),
            concat.encode("utf-8"),
            hashlib.sha256,
        )
        .hexdigest()
        .lower()
    )
    params["sign"] = expected_sign

    assert validate_hmac(params, secret) is True


def test_validate_hmac_empty_secret():
    """Must return False when secret is empty."""
    params = {"amount": "100.00", "sign": "abc123"}
    assert validate_hmac(params, "") is False


def test_validate_hmac_missing_sign():
    """Must return False when sign is missing."""
    params = {"amount": "100.00"}
    assert validate_hmac(params, "secret") is False


def test_validate_hmac_wrong_sign():
    """Must return False when sign does not match."""
    secret = "my_secret"
    params = {
        "amount": "100.00",
        "sign": "invalid_sign",
    }
    assert validate_hmac(params, secret) is False


def test_parse_label_valid():
    """Extracts telegram_id, payment_type, quantity correctly from labels."""
    # Old format: {id}_{hex} — defaults to 30-day monthly
    assert parse_label("12345_abc123") == (12345, "monthly", 30)
    assert parse_label("999_ffffffff") == (999, "monthly", 30)
    # New format: {id}_{type}_{quantity}_{hex}
    assert parse_label("12345_monthly_30_abc123") == (12345, "monthly", 30)
    assert parse_label("12345_monthly_90_abc123") == (12345, "monthly", 90)
    assert parse_label("12345_monthly_180_abc123") == (12345, "monthly", 180)
    assert parse_label("12345_tokens_5_abc123") == (12345, "tokens", 5)
    assert parse_label("999_tokens_10_deadbeef") == (999, "tokens", 10)


def test_parse_label_invalid():
    """Returns (0, 'monthly', 30) on bad input."""
    assert parse_label("") == (0, "monthly", 30)
    assert parse_label("no_underscore") == (0, "monthly", 30)
    assert parse_label("_only_underscore") == (0, "monthly", 30)
    assert parse_label("abc_123") == (0, "monthly", 30)


def test_verify_payment_wallet_api():
    """Mock requests.post and verify correct endpoint/headers/data."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "success"}
    mock_response.raise_for_status = MagicMock()

    with patch(
        "src.payments.yoomoney.requests.post",
        return_value=mock_response,
    ) as mock_post:
        result = verify_payment_wallet_api("op-123", "token-abc")

    mock_post.assert_called_once_with(
        "https://yoomoney.ru/api/operation-details",
        headers={
            "Authorization": "Bearer token-abc",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"operation_id": "op-123"},
        timeout=30,
    )
    assert result == {"status": "success"}


def test_build_payment_url_with_existing_label():
    """build_payment_url creates a valid URL with the given label."""
    from src.payments.yoomoney import build_payment_url

    url = build_payment_url(199.0, "4100112345678", "12345_existinglabel")
    assert "4100112345678" in url
    assert "199.00" in url
    assert "12345_existinglabel" in url
    assert url.startswith("https://yoomoney.ru/quickpay/confirm.xml?")


def test_create_payment_link_and_build_url_produce_same_format():
    """Both functions produce URLs with the same structure."""
    from src.payments.yoomoney import build_payment_url, create_payment_link

    url_new, label = create_payment_link(12345, 199.0, "4100112345678")
    url_reuse = build_payment_url(199.0, "4100112345678", label)
    # Both should have the same base URL and parameters (except label matches)
    assert url_new.split("?")[0] == url_reuse.split("?")[0]
    assert f"label={label}" in url_reuse
