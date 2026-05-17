"""Сервис управления подписками."""
from datetime import UTC, datetime, timedelta
from typing import cast

from loguru import logger

from src.db.models import Subscription
from src.payments import repository


def _make_aware(dt: datetime) -> datetime:
    """Присоединяет UTC к наивной дате из БД; осознанные — без изменений."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _is_monthly_active(telegram_id: int) -> bool:
    """Проверяет, активна ли месячная подписка (не истёкшая)."""
    subscription = repository.get_subscription(telegram_id)
    if subscription is None or subscription.status != "active":
        return False
    if subscription.expires_at is not None and _make_aware(subscription.expires_at) < datetime.now(UTC):
        return False
    return True


def has_tokens(telegram_id: int) -> bool:
    """Проверяет, есть ли у пользователя токены для прогнозов."""
    return repository.get_token_count(telegram_id) > 0


def is_subscribed(telegram_id: int) -> bool:
    """Проверяет, есть ли у пользователя доступ к прогнозам.

    Приоритет: месячная подписка > токены.
    Если месячная подписка истекла, проверяет наличие токенов.
    """
    # Monthly sub has priority
    if _is_monthly_active(telegram_id):
        return True

    # Auto-expire monthly sub if needed
    subscription = repository.get_subscription(telegram_id)
    if subscription is not None and subscription.status == "active" and subscription.expires_at is not None:
        if _make_aware(subscription.expires_at) < datetime.now(UTC):
            logger.info("Auto-expiring subscription: user={}", telegram_id)
            repository.upsert_subscription(
                telegram_id=telegram_id,
                status="inactive",
                expires_at=cast(datetime | None, subscription.expires_at),
                transaction_id=cast(str, subscription.transaction_id) or "",
            )

    # Check tokens
    has = has_tokens(telegram_id)
    if has:
        logger.debug("User has tokens: user={} count={}", telegram_id, repository.get_token_count(telegram_id))
    return has


def activate_subscription(
    telegram_id: int,
    amount: float,
    operation_id: str,
    duration_days: int = 30,
) -> Subscription:
    """Активирует или продлевает месячную подписку пользователя."""
    existing = repository.get_subscription(telegram_id)
    base_time = datetime.now(UTC)

    if duration_days > 0:
        existing_expires = (
            _make_aware(cast(datetime, existing.expires_at))
            if existing and existing.expires_at is not None
            else None
        )
        if (
            existing is not None
            and existing.status == "active"
            and existing_expires is not None
            and existing_expires > base_time
        ):
            base_time = existing_expires
        expires_at = base_time + timedelta(days=duration_days)
    else:
        expires_at = None

    # Preserve existing tokens when activating monthly sub
    current_tokens = existing.tokens if existing else 0

    logger.info("Activating subscription: user={} days={} expires_at={} op_id={}", telegram_id, duration_days, expires_at, operation_id)
    subscription = repository.upsert_subscription(
        telegram_id=telegram_id,
        status="active",
        expires_at=expires_at,
        transaction_id=operation_id,
        tokens=current_tokens,
    )

    return subscription


def add_tokens(telegram_id: int, count: int) -> Subscription:
    """Добавляет токены пользователю. Токены сохраняются даже при активной подписке."""
    return repository.add_tokens(telegram_id, count)


def consume_token(telegram_id: int) -> Subscription | None:
    """Списывает 1 токен. Возвращает None если токенов нет.

    Токены списываются только когда месячная подписка НЕ активна.
    """
    if _is_monthly_active(telegram_id):
        # Monthly sub active — no token consumption needed
        return repository.get_subscription(telegram_id)
    result = repository.consume_token(telegram_id)
    if result:
        logger.info("Token consumed: user={} remaining={}", telegram_id, result.tokens)
    else:
        logger.warning("Token consume failed: user={} no tokens", telegram_id)
    return result


def get_subscription_info(telegram_id: int) -> dict:
    """Возвращает информацию о подписке и последнем платеже."""
    subscription = repository.get_subscription(telegram_id)
    last_payment = repository.get_last_payment(telegram_id)

    last_payment_amount: float | None = None
    last_payment_date: datetime | None = None
    if last_payment is not None:
        last_payment_amount = cast(float, last_payment.amount)
        last_payment_date = cast(datetime | None, last_payment.paid_at) or cast(
            datetime, last_payment.created_at
        )

    token_count = subscription.tokens if subscription else 0
    monthly_active = _is_monthly_active(telegram_id)

    return {
        "status": subscription.status if subscription else "inactive",
        "expires_at": subscription.expires_at if subscription else None,
        "is_active": is_subscribed(telegram_id),
        "monthly_active": monthly_active,
        "tokens": token_count,
        "last_payment_amount": last_payment_amount,
        "last_payment_date": last_payment_date,
    }
