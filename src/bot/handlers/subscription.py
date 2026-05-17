"""Обработчики подписки и управления доступом."""
from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.keyboards import (
    get_main_reply_keyboard,
    get_subscription_inline_keyboard,
    get_subscription_type_keyboard,
    get_token_count_keyboard,
)
from src.bot.localization import (
    SUBSCRIPTION_NONE,
    SUBSCRIPTION_STATUS_ACTIVE,
    SUBSCRIPTION_STATUS_INACTIVE,
    SUB_TYPE_PROMPT,
    TIER_DISPLAY,
    TOKEN_PURCHASE_PROMPT,
    TOKEN_PURCHASE_TOTAL,
    format_subscription_info,
    format_subscription_prompt,
)
from src.bot.states import SubscriptionStates
from src.core.config import settings
from src.payments.repository import create_payment, get_pending_payment
from src.payments.subscription import get_subscription_info, is_subscribed
from src.payments.yoomoney import build_payment_url, create_payment_link


def _make_aware(dt: datetime) -> datetime:
    """Присоединяет UTC к наивной дате из БД."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


router = Router(name="subscription")


async def send_subscription_prompt(message: Message, telegram_id: int) -> None:
    """Отправляет приглашение выбрать тип подписки."""
    token_price = int(settings.token_price)
    await message.answer(
        f"{SUBSCRIPTION_NONE}\n\n{SUB_TYPE_PROMPT}",
        parse_mode="HTML",
        reply_markup=get_subscription_type_keyboard(settings.SUBSCRIPTION_TIERS, token_price),
    )


async def _send_monthly_payment_link(
    target: Message | CallbackQuery, telegram_id: int, duration_days: int,
) -> None:
    """Отправляет ссылку на оплату месячной подписки выбранного тарифа."""
    price = float(settings.SUBSCRIPTION_TIERS[duration_days])

    pending = get_pending_payment(telegram_id)
    if pending is not None and str(pending.payment_type) == "monthly":
        label = str(pending.label)
        url = build_payment_url(price, settings.yoomoney_receiver_wallet, label)
    else:
        url, label = create_payment_link(
            telegram_id, price, settings.yoomoney_receiver_wallet,
            payment_type="monthly", quantity=duration_days,
        )
        create_payment(telegram_id, price, label, payment_type="monthly", token_count=0)

    tier_label = TIER_DISPLAY.get(duration_days, f"{duration_days // 30} мес.")
    text = f"{SUBSCRIPTION_NONE}\n\n{format_subscription_prompt(int(price))} ({tier_label})"
    if isinstance(target, CallbackQuery):
        if target.message is not None:
            await target.message.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=get_subscription_inline_keyboard(url, int(price)),
            )
    else:
        await target.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_subscription_inline_keyboard(url, int(price)),
        )


async def _send_token_payment_link(
    target: Message | CallbackQuery, telegram_id: int, token_count: int,
) -> None:
    """Отправляет ссылку на оплату токенов."""
    token_price = settings.token_price
    total_price = token_price * token_count

    url, label = create_payment_link(
        telegram_id, total_price, settings.yoomoney_receiver_wallet,
        payment_type="tokens", quantity=token_count,
    )
    create_payment(
        telegram_id, total_price, label,
        payment_type="tokens", token_count=token_count,
    )

    text = TOKEN_PURCHASE_TOTAL.format(count=token_count, total=int(total_price))
    if isinstance(target, CallbackQuery):
        if target.message is not None:
            await target.message.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=get_subscription_inline_keyboard(url, int(total_price)),
            )
    else:
        await target.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_subscription_inline_keyboard(url, int(total_price)),
        )


def _format_info_text(telegram_id: int) -> str | None:
    """Build subscription info text, or None if user has no subscription."""
    info = get_subscription_info(telegram_id)
    if not info["is_active"] and info["status"] == "inactive" and info["expires_at"] is None and info["tokens"] == 0:
        return None
    status = SUBSCRIPTION_STATUS_ACTIVE if info["is_active"] else SUBSCRIPTION_STATUS_INACTIVE
    expires_at = str(info["expires_at"]) if info["expires_at"] else None
    price = min(settings.SUBSCRIPTION_TIERS.values())
    # Unlimited: active with no expiry → days=None → shows "навсегда"
    # Limited: calculate remaining days from actual expiry
    if info["monthly_active"] and info["expires_at"] is None:
        days = None
    elif info["expires_at"] is not None:
        remaining = _make_aware(info["expires_at"]) - datetime.now(UTC)
        days = max(0, remaining.days)
    else:
        days = None
    last_amount = int(info["last_payment_amount"]) if info["last_payment_amount"] else None
    last_date = str(info["last_payment_date"]) if info["last_payment_date"] else None
    return format_subscription_info(
        status=status,
        expires_at=expires_at,
        price=price,
        days=days,
        last_amount=last_amount,
        last_date=last_date,
        tokens=info["tokens"],
        monthly_active=info["monthly_active"],
    )


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message) -> None:
    """Обрабатывает команду /subscribe — показывает статус или предложение оплатить."""
    if message.from_user is None:
        return
    telegram_id = message.from_user.id
    if is_subscribed(telegram_id):
        text = _format_info_text(telegram_id)
        if text:
            await message.answer(text, parse_mode="HTML", reply_markup=get_main_reply_keyboard())
    else:
        await send_subscription_prompt(message, telegram_id)


@router.message(F.text == "💳 Подписка")
async def btn_subscribe(message: Message) -> None:
    """Обрабатывает кнопку '💳 Подписка' — аналогично /subscribe."""
    if message.from_user is None:
        return
    telegram_id = message.from_user.id
    if is_subscribed(telegram_id):
        text = _format_info_text(telegram_id)
        if text:
            await message.answer(text, parse_mode="HTML", reply_markup=get_main_reply_keyboard())
    else:
        await send_subscription_prompt(message, telegram_id)


@router.callback_query(F.data == "cmd:subscribe")
async def cmd_subscribe_callback(callback: CallbackQuery) -> None:
    """Обрабатывает inline-кнопку 'cmd:subscribe' — обновляет сообщение."""
    if callback.from_user is None:
        await callback.answer()
        return
    telegram_id = callback.from_user.id
    if is_subscribed(telegram_id):
        text = _format_info_text(telegram_id)
        if text and callback.message is not None:
            await callback.message.edit_text(text, parse_mode="HTML")
    else:
        token_price = int(settings.token_price)
        text = f"{SUBSCRIPTION_NONE}\n\n{SUB_TYPE_PROMPT}"
        if callback.message is not None:
            await callback.message.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=get_subscription_type_keyboard(settings.SUBSCRIPTION_TIERS, token_price),
            )
    await callback.answer()


# ── Выбор тарифа подписки ────────────────────────────────────


@router.callback_query(F.data.startswith("sub:monthly:"))
async def cb_sub_monthly(callback: CallbackQuery) -> None:
    """Обрабатывает выбор тарифа месячной подписки."""
    if callback.from_user is None:
        await callback.answer()
        return
    duration_days = int(callback.data.split(":")[-1])
    await _send_monthly_payment_link(callback, callback.from_user.id, duration_days)
    await callback.answer()


@router.callback_query(F.data == "sub:tokens")
async def cb_sub_tokens(callback: CallbackQuery, state: FSMContext) -> None:
    """Обрабатывает выбор покупки токенов — показывает выбор количества."""
    token_price = int(settings.token_price)
    text = TOKEN_PURCHASE_PROMPT
    if callback.message is not None:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_token_count_keyboard(token_price),
        )
    await state.set_state(SubscriptionStates.selecting_token_count)
    await callback.answer()


@router.callback_query(F.data.startswith("sub:tokens:"))
async def cb_sub_tokens_count(callback: CallbackQuery, state: FSMContext) -> None:
    """Обрабатывает выбор количества токенов — создаёт ссылку на оплату."""
    if callback.from_user is None:
        await callback.answer()
        return
    token_count = int(callback.data.split(":")[-1])
    await _send_token_payment_link(callback, callback.from_user.id, token_count)
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "sub:type_select")
async def cb_sub_type_select(callback: CallbackQuery, state: FSMContext) -> None:
    """Возвращает к выбору типа подписки."""
    if callback.from_user is None:
        await callback.answer()
        return
    token_price = int(settings.token_price)
    text = f"{SUBSCRIPTION_NONE}\n\n{SUB_TYPE_PROMPT}"
    if callback.message is not None:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_subscription_type_keyboard(settings.SUBSCRIPTION_TIERS, token_price),
        )
    await state.clear()
    await callback.answer()
