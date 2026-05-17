"""Pure-function YooMoney payment utilities."""

import hashlib
import hmac
import secrets
import urllib.parse
from typing import Any

import requests
from loguru import logger


def create_payment_link(
    telegram_id: int, price: float, wallet: str,
    payment_type: str = "monthly", quantity: int = 0,
) -> tuple[str, str]:
    """Build a YooMoney Quickpay URL and correlation label.

    Label format: {telegram_id}_{payment_type}_{quantity}_{random_hex}
    For monthly: quantity = duration_days (30, 90, 180)
    For tokens:  quantity = token_count (1, 5, 10, 25)
    Examples: 123_monthly_30_a3f1b2c4  |  123_tokens_5_d5e6f7g8
    """
    label = f"{telegram_id}_{payment_type}_{quantity}_{secrets.token_hex(8)}"
    url = build_payment_url(price, wallet, label)
    logger.info("Payment link created: user={} type={} amount={} label={}", telegram_id, payment_type, price, label)
    return url, label


def build_payment_url(price: float, wallet: str, label: str) -> str:
    """Build a YooMoney Quickpay URL for an existing label."""
    params = {
        "receiver": wallet,
        "quickpay-form": "shop",
        "sum": f"{price:.2f}",
        "label": label,
        "targets": "Telegram bot subscription",
    }
    query = urllib.parse.urlencode(params)
    return f"https://yoomoney.ru/quickpay/confirm.xml?{query}"


def validate_hmac(params: dict[str, str], secret: str) -> bool:
    """Validate YooMoney webhook HMAC-SHA256 signature."""
    if not secret:
        return False

    received_sign = params.get("sign", "")
    if not received_sign:
        return False

    params_no_sign = {k: v for k, v in params.items() if k != "sign"}
    sorted_params = sorted(params_no_sign.items(), key=lambda x: x[0])
    concat = "&".join(
        f"{k}={urllib.parse.quote(v, safe='')}" for k, v in sorted_params
    )

    computed = (
        hmac.new(
            secret.encode("utf-8"),
            concat.encode("utf-8"),
            hashlib.sha256,
        )
        .hexdigest()
        .lower()
    )

    return hmac.compare_digest(computed, received_sign.lower())


def verify_payment_wallet_api(
    operation_id: str, access_token: str
) -> dict[str, Any]:
    """Verify a payment via YooMoney Wallet API."""
    try:
        response = requests.post(
            "https://yoomoney.ru/api/operation-details",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"operation_id": operation_id},
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        logger.info("Payment verified via API: op_id={} status={}", operation_id, result.get("status", "unknown"))
        return result
    except Exception as exc:
        logger.error("Payment verification failed: op_id={} error={}", operation_id, exc)
        return {"error": str(exc), "status": "unknown"}


def parse_label(label: str) -> tuple[int, str, int]:
    """Extract telegram_id, payment_type, and quantity from a label.

    Returns (telegram_id, payment_type, quantity):
      - For monthly: quantity = duration_days (30, 90, 180)
      - For tokens:  quantity = token_count

    Old format: {telegram_id}_{hex} → (telegram_id, "monthly", 30)
    New format: {telegram_id}_{type}_{quantity}_{hex} → (telegram_id, type, quantity)
    """
    parts = label.split("_")
    try:
        telegram_id = int(parts[0])
    except (ValueError, IndexError):
        return 0, "monthly", 30

    if len(parts) == 2:
        # Old format: {id}_{hex} — assume default 30-day monthly
        return telegram_id, "monthly", 30

    if len(parts) >= 4:
        # New format: {id}_{type}_{quantity}_{hex}
        payment_type = parts[1]
        try:
            quantity = int(parts[2])
        except ValueError:
            quantity = 30 if payment_type == "monthly" else 0
        return telegram_id, payment_type, quantity

    return telegram_id, "monthly", 30
