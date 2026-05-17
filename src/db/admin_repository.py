"""Репозиторий для административных запросов к базе данных."""
from datetime import UTC, datetime, timedelta
from typing import cast

from loguru import logger
from peewee import fn

from src.db.models import Forecast, Payment, Subscription, User
from src.payments.repository import upsert_subscription
from src.payments.subscription import activate_subscription


def _make_aware(dt: datetime) -> datetime:
    """Присоединяет UTC к наивной дате из БД; осознанные — без изменений."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def get_all_users(limit: int = 20, offset: int = 0) -> list[User]:
    """Возвращает список пользователей с пагинацией."""
    return (
        User.select()
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )


def get_users_count() -> int:
    """Возвращает общее количество пользователей."""
    return User.select().count()


def get_user_by_telegram_id(telegram_id: int) -> User | None:
    """Возвращает пользователя по Telegram ID."""
    try:
        return User.get(User.telegram_id == telegram_id)
    except User.DoesNotExist:
        return None


def get_user_detail(telegram_id: int) -> dict:
    """Возвращает детальную информацию о пользователе."""
    user = get_user_by_telegram_id(telegram_id)
    if user is None:
        return {}

    forecasts_count = (
        Forecast.select().where(Forecast.user == user).count()
    )
    subscription = get_user_subscription(telegram_id)
    last_payment = get_user_last_payment(telegram_id)

    return {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "language_code": user.language_code,
        "created_at": user.created_at,
        "forecasts_count": forecasts_count,
        "subscription": subscription,
        "last_payment": last_payment,
    }


def get_user_subscription(telegram_id: int) -> Subscription | None:
    """Возвращает подписку пользователя."""
    try:
        return Subscription.get_by_id(telegram_id)
    except Subscription.DoesNotExist:
        return None


def get_user_last_payment(telegram_id: int) -> Payment | None:
    """Возвращает последний платёж пользователя."""
    return (
        Payment.select()
        .where(
            Payment.telegram_id == telegram_id,
            Payment.status == "completed",
        )
        .order_by(Payment.paid_at.desc())
        .first()
    )


def activate_user_subscription(
    telegram_id: int, duration_days: int = 30
) -> Subscription:
    """Активирует подписку пользователя на указанное количество дней."""
    logger.info("Admin activate subscription: user={} days={}", telegram_id, duration_days)
    return activate_subscription(
        telegram_id=telegram_id,
        amount=0,
        operation_id="admin_grant",
        duration_days=duration_days,
    )


def deactivate_user_subscription(telegram_id: int) -> Subscription | None:
    """Деактивирует подписку пользователя."""
    subscription = get_user_subscription(telegram_id)
    if subscription is None:
        return None

    logger.info("Admin deactivate subscription: user={}", telegram_id)
    return upsert_subscription(
        telegram_id=telegram_id,
        status="inactive",
        expires_at=cast(datetime | None, subscription.expires_at),
        transaction_id=cast(str, subscription.transaction_id) or "",
    )


def extend_user_subscription(
    telegram_id: int, extra_days: int
) -> Subscription | None:
    """Продлевает подписку пользователя на указанное количество дней."""
    subscription = get_user_subscription(telegram_id)
    if subscription is None:
        return None

    current_expires = cast(datetime | None, subscription.expires_at)
    base = (
        _make_aware(current_expires)
        if current_expires and subscription.status == "active" and _make_aware(current_expires) > datetime.now(UTC)
        else datetime.now(UTC)
    )

    new_expires = base + timedelta(days=extra_days)
    logger.info("Admin extend subscription: user={} days={} new_expires={}", telegram_id, extra_days, new_expires)
    return upsert_subscription(
        telegram_id=telegram_id,
        status="active",
        expires_at=new_expires,
        transaction_id=cast(str, subscription.transaction_id) or "admin_extend",
    )


def shrink_user_subscription(
    telegram_id: int, reduce_days: int
) -> Subscription | None:
    """Уменьшает срок подписки пользователя на указанное количество дней."""
    subscription = get_user_subscription(telegram_id)
    if subscription is None:
        return None

    current_expires = cast(datetime | None, subscription.expires_at)
    if current_expires is None:
        return subscription

    new_expires = _make_aware(current_expires) - timedelta(days=reduce_days)
    now = datetime.now(UTC)
    if new_expires <= now:
        new_expires = now
        status = "inactive"
    else:
        status = "active"

    logger.info("Admin shrink subscription: user={} days={} new_expires={} status={}", telegram_id, reduce_days, new_expires, status)
    return upsert_subscription(
        telegram_id=telegram_id,
        status=status,
        expires_at=new_expires,
        transaction_id=cast(str, subscription.transaction_id) or "admin_shrink",
    )


# ── Статистика ─────────────────────────────────────────────


def get_daily_forecast_stats(days: int = 30) -> list[dict]:
    """Возвращает ежедневную статистику прогнозов за последние N дней."""
    since = datetime.now(UTC) - timedelta(days=days)
    since_naive = since.replace(tzinfo=None)
    rows = (
        Forecast
        .select(
            fn.date(Forecast.created_at).alias("date"),
            fn.count(Forecast.id).alias("count"),
        )
        .where(Forecast.created_at >= since_naive)
        .group_by(fn.date(Forecast.created_at))
        .order_by(fn.date(Forecast.created_at))
    )
    return [{"date": row.date, "count": row.count} for row in rows]


def get_monthly_forecast_stats(months: int = 12) -> list[dict]:
    """Возвращает помесячную статистику прогнозов за последние N месяцев."""
    since = datetime.now(UTC) - timedelta(days=months * 30)
    since_naive = since.replace(tzinfo=None)
    rows = (
        Forecast
        .select(
            fn.strftime("%Y-%m", Forecast.created_at).alias("month"),
            fn.count(Forecast.id).alias("count"),
        )
        .where(Forecast.created_at >= since_naive)
        .group_by(fn.strftime("%Y-%m", Forecast.created_at))
        .order_by(fn.strftime("%Y-%m", Forecast.created_at))
    )
    return [{"month": row.month, "count": row.count} for row in rows]


def get_subscription_stats() -> dict:
    """Возвращает статистику подписок: активные, неактивные, всего."""
    active = Subscription.select().where(Subscription.status == "active").count()
    total = Subscription.select().count()
    return {
        "active": active,
        "inactive": total - active,
        "total": total,
    }


def get_revenue_stats(days: int = 30) -> list[dict]:
    """Возвращает ежедневную выручку за последние N дней."""
    since = datetime.now(UTC) - timedelta(days=days)
    since_naive = since.replace(tzinfo=None)
    rows = (
        Payment
        .select(
            fn.date(Payment.paid_at).alias("date"),
            fn.sum(Payment.amount).alias("total"),
            fn.count(Payment.id).alias("count"),
        )
        .where(
            Payment.status == "completed",
            Payment.paid_at >= since_naive,
        )
        .group_by(fn.date(Payment.paid_at))
        .order_by(fn.date(Payment.paid_at))
    )
    return [
        {"date": row.date, "total": float(row.total) if row.total else 0, "count": row.count}
        for row in rows
    ]


def get_overall_stats() -> dict:
    """Возвращает общую статистику для административной панели."""
    total_users = get_users_count()
    total_forecasts = Forecast.select().count()
    sub_stats = get_subscription_stats()
    total_revenue = (
        Payment.select(fn.sum(Payment.amount)).where(Payment.status == "completed").scalar()
    )

    return {
        "total_users": total_users,
        "total_forecasts": total_forecasts,
        "active_subscriptions": sub_stats["active"],
        "inactive_subscriptions": sub_stats["inactive"],
        "total_subscriptions": sub_stats["total"],
        "total_revenue": float(total_revenue) if total_revenue else 0.0,
    }
