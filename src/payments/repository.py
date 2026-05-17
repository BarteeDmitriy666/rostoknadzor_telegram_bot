"""Репозиторий для операций с подписками и платежами."""
from datetime import UTC, datetime

from loguru import logger
from peewee import DoesNotExist

from src.db.models import Payment, Subscription


def get_subscription(telegram_id: int) -> Subscription | None:
    """Возвращает подписку пользователя по Telegram ID."""
    try:
        return Subscription.get_by_id(telegram_id)
    except DoesNotExist:
        return None


def upsert_subscription(
    telegram_id: int,
    status: str,
    expires_at: datetime | None,
    transaction_id: str,
    tokens: int | None = None,
) -> Subscription:
    """Создаёт новую или обновляет существующую подписку."""
    subscription, created = Subscription.get_or_create(
        telegram_id=telegram_id,
        defaults={
            "status": status,
            "expires_at": expires_at,
            "activated_at": datetime.now(UTC),
            "transaction_id": transaction_id,
            "tokens": tokens if tokens is not None else 0,
        },
    )
    if not created:
        subscription.status = status
        subscription.expires_at = expires_at
        subscription.activated_at = datetime.now(UTC)
        subscription.transaction_id = transaction_id
        if tokens is not None:
            subscription.tokens = tokens
        subscription.save()
    action = "created" if created else "updated"
    logger.info("Subscription {}: user={} status={} tokens={}", action, telegram_id, status, subscription.tokens)
    return subscription


def add_tokens(telegram_id: int, count: int) -> Subscription:
    """Добавляет токены к подписке пользователя. Создаёт подписку при необходимости."""
    subscription = get_subscription(telegram_id)
    current_tokens = subscription.tokens if subscription else 0
    new_tokens = current_tokens + count
    logger.info("Adding tokens: user={} added={} new_total={}", telegram_id, count, new_tokens)
    return upsert_subscription(
        telegram_id=telegram_id,
        status=subscription.status if subscription else "inactive",
        expires_at=subscription.expires_at if subscription else None,
        transaction_id=subscription.transaction_id if subscription else "token_purchase",
        tokens=new_tokens,
    )


def consume_token(telegram_id: int) -> Subscription | None:
    """Списывает 1 токен у пользователя. Возвращает None если токенов нет."""
    subscription = get_subscription(telegram_id)
    if subscription is None or subscription.tokens <= 0:
        return None
    subscription.tokens -= 1
    subscription.save()
    logger.info("Token consumed: user={} remaining={}", telegram_id, subscription.tokens)
    return subscription


def get_token_count(telegram_id: int) -> int:
    """Возвращает количество токенов пользователя."""
    subscription = get_subscription(telegram_id)
    return subscription.tokens if subscription else 0


def create_payment(
    telegram_id: int,
    amount: float,
    label: str,
    payment_type: str = "monthly",
    token_count: int = 0,
) -> Payment:
    """Создаёт запись о платеже со статусом 'pending'."""
    payment = Payment.create(
        telegram_id=telegram_id,
        amount=amount,
        label=label,
        status="pending",
        payment_type=payment_type,
        token_count=token_count,
    )
    logger.info("Payment created: id={} user={} amount={} type={} label={}", payment.id, telegram_id, amount, payment_type, label)
    return payment


def update_payment_status(
    label: str,
    yoomoney_op_id: str,
    status: str,
) -> Payment | None:
    """Обновляет статус платежа по метке."""
    try:
        payment = Payment.get(Payment.label == label)
    except DoesNotExist:
        logger.warning("Payment update failed: label={} not found", label)
        return None

    payment.status = status
    payment.yoomoney_op_id = yoomoney_op_id
    if status == "completed":
        payment.paid_at = datetime.now(UTC)
    payment.save()
    logger.info("Payment status updated: id={} label={} status={} op_id={}", payment.id, label, status, yoomoney_op_id)
    return payment


def get_payment_by_label(label: str) -> Payment | None:
    """Возвращает платёж по метке."""
    try:
        return Payment.get(Payment.label == label)
    except DoesNotExist:
        return None


def get_payment_by_operation_id(yoomoney_op_id: str) -> Payment | None:
    """Возвращает платёж по ID операции YooMoney."""
    try:
        return Payment.get(Payment.yoomoney_op_id == yoomoney_op_id)
    except DoesNotExist:
        return None


def get_last_payment(telegram_id: int) -> Payment | None:
    """Возвращает последний завершённый платёж пользователя."""
    return (
        Payment.select()
        .where(
            Payment.telegram_id == telegram_id,
            Payment.status == "completed",
        )
        .order_by(Payment.paid_at.desc())
        .first()
    )


def get_pending_payment(telegram_id: int) -> Payment | None:
    """Возвращает текущий ожидающий платёж пользователя, если есть."""
    return (
        Payment.select()
        .where(
            Payment.telegram_id == telegram_id,
            Payment.status == "pending",
        )
        .order_by(Payment.created_at.desc())
        .first()
    )
