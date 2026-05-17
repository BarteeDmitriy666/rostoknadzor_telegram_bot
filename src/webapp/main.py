"""FastAPI webhook server for YooMoney notifications."""
import asyncio
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from loguru import logger
import uvicorn

from src.core.config import settings
from src.db import init_database
from src.payments import repository
from src.payments.subscription import (
    activate_subscription,
    add_tokens,
    get_subscription_info,
)
from src.payments.yoomoney import (
    parse_label,
    validate_hmac,
    verify_payment_wallet_api,
)

# Notification strings (duplicated from bot.localization to avoid circular import)
_ACTIVATED = "✅ Подписка активирована! Доступ к прогнозам открыт."
_ACTIVATED_WITH_EXPIRY = "✅ Подписка активирована до <b>{expires_at}</b>! Доступ к прогнозам открыт."
_ACTIVATED_FOREVER = "✅ Подписка активирована <b>навсегда</b>! Доступ к прогнозам открыт."
_TOKENS_PURCHASED = (
    "✅ Токены успешно приобретены в количестве: <b>{count}</b>, "
    "вы можете тратить токены делая прогнозы."
)

app = FastAPI()


def _form_to_dict(form: Any) -> dict[str, str]:
    """Convert multipart/form-data to flat string dict."""
    return {k: str(v) for k, v in form.items()}


def _is_already_processed(operation_id: str) -> bool:
    """Idempotency check: payment already completed."""
    payment = repository.get_payment_by_operation_id(operation_id)
    if payment is None:
        return False
    return str(payment.status) == "completed"


def _verify_via_wallet(operation_id: str) -> bool:
    """Optional Wallet API verification — never blocks on error."""
    if not settings.yoomoney_access_token.strip():
        return True
    try:
        response = verify_payment_wallet_api(
            operation_id, settings.yoomoney_access_token
        )
        if "error" in response:
            logger.warning(f"Wallet API error for {operation_id}: {response['error']}")
            return True  # Trust the webhook on API failure
        return response.get("status") == "success"
    except Exception as exc:
        logger.warning(f"Wallet API exception for {operation_id}: {exc}")
        return True  # Trust the webhook on any failure


def _build_monthly_activation_text(telegram_id: int) -> str:
    """Build the activation notification text for monthly subscription."""
    info = get_subscription_info(telegram_id)
    expires_at = info.get("expires_at")
    if expires_at is not None:
        return _ACTIVATED_WITH_EXPIRY.format(
            expires_at=expires_at.strftime("%d.%m.%Y")
        )
    if info.get("monthly_active") and expires_at is None:
        return _ACTIVATED_FOREVER
    return _ACTIVATED


def _build_token_activation_text(token_count: int) -> str:
    """Build the activation notification text for token purchase."""
    return _TOKENS_PURCHASED.format(count=token_count)


async def _notify_user(bot: Any, telegram_id: int, text: str) -> None:
    """Send notification to the user via the bot."""
    try:
        await bot.send_message(telegram_id, text, parse_mode="HTML")
        logger.info(f"Notification sent to {telegram_id}")
    except Exception as exc:
        logger.warning(f"Failed to send notification to {telegram_id}: {exc}")


@app.post("/webhooks/yoomoney/notification")
async def handle_notification(request: Request) -> dict[str, str]:
    """Receive and process YooMoney payment webhooks."""
    form = await request.form()
    params = _form_to_dict(form)

    if not validate_hmac(params, settings.yoomoney_notification_secret):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    if params.get("test_notification") == "true":
        return {"status": "ok"}

    if params.get("notification_type") not in ("p2p-incoming", "card-incoming"):
        return {"status": "ok"}

    label = params.get("label", "")
    telegram_id, payment_type, quantity = parse_label(label)
    if telegram_id == 0:
        return {"status": "ok"}

    operation_id = params.get("operation_id", "")
    amount = float(params.get("amount", "0"))

    # Validate payment amount based on payment type
    if payment_type == "tokens":
        expected_price = settings.token_price * quantity
    else:
        # quantity = duration_days for monthly; look up tier price
        expected_price = float(settings.SUBSCRIPTION_TIERS.get(quantity, min(settings.SUBSCRIPTION_TIERS.values())))

    # YooMoney deducts commission, so the received amount is lower.
    # Accept ≥90% of expected price.
    min_acceptable = expected_price * 0.9
    if amount < min_acceptable:
        logger.warning(
            f"Amount {amount} below minimum acceptable {min_acceptable} "
            f"(expected {expected_price}, type={payment_type}, qty={quantity}) for operation {operation_id}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    if _is_already_processed(operation_id):
        return {"status": "ok"}

    if not _verify_via_wallet(operation_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    # Route based on payment type
    if payment_type == "tokens":
        add_tokens(telegram_id, quantity)
        notification_text = _build_token_activation_text(quantity)
    else:
        # quantity = duration_days for monthly subscription
        activate_subscription(
            telegram_id,
            amount,
            operation_id,
            duration_days=quantity,
        )
        notification_text = _build_monthly_activation_text(telegram_id)

    repository.update_payment_status(label, operation_id, "completed")

    # Notify user via Telegram bot
    bot = getattr(request.app.state, "bot", None)
    if bot is not None:
        asyncio.create_task(_notify_user(bot, telegram_id, notification_text))

    return {"status": "ok"}


async def run_webhook_server() -> None:
    """Run uvicorn on the configured webhook port."""
    init_database()
    config = uvicorn.Config(app, host="0.0.0.0", port=settings.webhook_port, log_level="info")
    server = uvicorn.Server(config)
    logger.info(f"Starting webhook server on port {settings.webhook_port}")
    await server.serve()
