"""Обработчики административной панели."""
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from loguru import logger

from src.bot.admin_charts import (
    generate_daily_usage_chart,
    generate_monthly_usage_chart,
    generate_revenue_chart,
    generate_subscription_chart,
)
from src.bot.keyboards import (
    get_admin_menu_keyboard,
    get_admin_stats_keyboard,
    get_admin_user_actions_keyboard,
    get_admin_users_keyboard,
)
from src.bot.localization import (
    ADMIN_DENIED,
    ADMIN_FIND_BY_ID_INVALID,
    ADMIN_FIND_BY_ID_NOT_FOUND,
    ADMIN_FIND_BY_ID_PROMPT,
    ADMIN_MENU_TITLE,
    ADMIN_NO_USERS,
    ADMIN_STATS_TITLE,
    ADMIN_SUB_ACTIVATED,
    ADMIN_SUB_DEACTIVATED,
    ADMIN_SUB_EXTENDED,
    ADMIN_SUB_FOREVER,
    ADMIN_SUB_NO_SUB,
    ADMIN_SUB_SHRUNK,
    ADMIN_TOKENS_ADDED,
    ADMIN_TOKENS_REMOVED,
    ADMIN_USER_DETAIL_TITLE,
    ADMIN_USER_NOT_FOUND,
    ADMIN_USERS_TITLE,
    format_admin_stats,
    format_admin_user_info,
)
from src.bot.states import AdminStates
from src.core.config import settings
from src.db import admin_repository
from src.db.connection import get_or_create_user
from src.payments import repository as payment_repository

router = Router(name="admin")


def _is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором."""
    return user_id in settings.admin_ids


def _guard(callback_or_message: CallbackQuery | Message) -> bool:
    """Проверяет доступ; отправляет отказ при отсутствии прав."""
    uid = callback_or_message.from_user.id if callback_or_message.from_user else 0
    allowed = _is_admin(uid)
    if not allowed:
        logger.warning("Admin access denied: user={}", uid)
    return allowed


async def _safe_edit_text(
    callback: CallbackQuery,
    text: str,
    reply_markup=None,
) -> None:
    """Редактирует сообщение, игнорируя ошибку 'content is not modified'."""
    if callback.message is None:
        return
    try:
        await callback.message.edit_text(
            text, parse_mode="HTML", reply_markup=reply_markup
        )
    except TelegramBadRequest:
        pass


def _render_user_detail(telegram_id: int) -> str | None:
    """Возвращает текст с актуальной информацией о пользователе."""
    detail = admin_repository.get_user_detail(telegram_id)
    if not detail:
        return None
    return f"{ADMIN_USER_DETAIL_TITLE}\n\n{format_admin_user_info(detail)}"


# ── Команда /admin ────────────────────────────────────────


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    """Открывает админ-панель."""
    uid = message.from_user.id if message.from_user else 0
    if not _is_admin(uid):
        logger.warning("Admin panel access denied: user={}", uid)
        await message.answer(ADMIN_DENIED, parse_mode="HTML")
        return
    logger.info("Admin panel opened: user={}", uid)
    await state.clear()
    await message.answer(
        ADMIN_MENU_TITLE, parse_mode="HTML", reply_markup=get_admin_menu_keyboard()
    )


# ── Навигация ─────────────────────────────────────────────


@router.callback_query(F.data == "admin:menu")
async def cb_admin_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Возвращает в меню админ-панели."""
    if not _guard(callback):
        await callback.answer(ADMIN_DENIED, show_alert=True)
        return
    await state.clear()
    await _safe_edit_text(callback, ADMIN_MENU_TITLE, get_admin_menu_keyboard())
    await callback.answer()


# ── Поиск по ID ───────────────────────────────────────────


@router.callback_query(F.data == "admin:find")
async def cb_admin_find(callback: CallbackQuery, state: FSMContext) -> None:
    """Запрашивает Telegram ID для поиска пользователя."""
    if not _guard(callback):
        await callback.answer(ADMIN_DENIED, show_alert=True)
        return
    await state.set_state(AdminStates.waiting_for_user_id)
    await _safe_edit_text(callback, ADMIN_FIND_BY_ID_PROMPT, get_admin_menu_keyboard())
    await callback.answer()


@router.message(AdminStates.waiting_for_user_id, F.text)
async def msg_admin_find_by_id(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод Telegram ID для поиска пользователя."""
    if not _is_admin(message.from_user.id if message.from_user else 0):
        await state.clear()
        return

    text = (message.text or "").strip()

    try:
        telegram_id = int(text)
    except ValueError:
        await message.answer(ADMIN_FIND_BY_ID_INVALID, parse_mode="HTML")
        return

    # Создаём User-запись, если пользователя нет в базе —
    # чтобы админ мог управлять подпиской/токенами нового пользователя.
    user = get_or_create_user(telegram_id=telegram_id)

    detail = admin_repository.get_user_detail(telegram_id)
    if not detail:
        # Маловероятно, но обработаем
        await message.answer(
            ADMIN_FIND_BY_ID_NOT_FOUND.format(telegram_id=telegram_id),
            parse_mode="HTML",
        )
        await state.clear()
        return

    info = f"{ADMIN_USER_DETAIL_TITLE}\n\n{format_admin_user_info(detail)}"
    await message.answer(
        info,
        parse_mode="HTML",
        reply_markup=get_admin_user_actions_keyboard(telegram_id),
    )
    await state.clear()


# ── Пользователи ──────────────────────────────────────────


@router.callback_query(F.data.startswith("admin:users:"))
async def cb_admin_users(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает список пользователей с пагинацией."""
    if not _guard(callback):
        await callback.answer(ADMIN_DENIED, show_alert=True)
        return

    page = int(callback.data.split(":")[-1])
    per_page = 10
    total_count = admin_repository.get_users_count()
    total_pages = max(1, (total_count + per_page - 1) // per_page)

    if total_count == 0:
        await _safe_edit_text(callback, ADMIN_NO_USERS, get_admin_menu_keyboard())
        await callback.answer()
        return

    users = list(admin_repository.get_all_users(limit=1000))

    await state.set_state(None)
    text = ADMIN_USERS_TITLE.format(page=page + 1, total_pages=total_pages)
    await _safe_edit_text(
        callback,
        text,
        get_admin_users_keyboard(users, page=page, per_page=per_page),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:user:"))
async def cb_admin_user_detail(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает детали пользователя и кнопки управления подпиской."""
    if not _guard(callback):
        await callback.answer(ADMIN_DENIED, show_alert=True)
        return

    telegram_id = int(callback.data.split(":")[-1])
    text = _render_user_detail(telegram_id)

    if text is None:
        await callback.answer(ADMIN_USER_NOT_FOUND, show_alert=True)
        return

    await state.set_state(None)
    await _safe_edit_text(
        callback, text, get_admin_user_actions_keyboard(telegram_id)
    )
    await callback.answer()


# ── Управление подписками ─────────────────────────────────


@router.callback_query(F.data.startswith("admin:sub:activate:"))
async def cb_admin_sub_activate(callback: CallbackQuery) -> None:
    """Активирует подписку пользователя."""
    if not _guard(callback):
        await callback.answer(ADMIN_DENIED, show_alert=True)
        return

    parts = callback.data.split(":")
    telegram_id = int(parts[3])
    days = int(parts[4])
    logger.info("Admin activate subscription: admin={} user={} days={}", callback.from_user.id, telegram_id, days)

    if days == 0:
        admin_repository.activate_user_subscription(telegram_id, duration_days=0)
        notice = ADMIN_SUB_FOREVER.format(telegram_id=telegram_id)
    else:
        admin_repository.activate_user_subscription(telegram_id, duration_days=days)
        notice = ADMIN_SUB_ACTIVATED.format(days=days, telegram_id=telegram_id)

    # Re-render user detail with fresh data + notice
    text = _render_user_detail(telegram_id)
    if text is not None:
        text = f"{notice}\n\n{text}"
    else:
        text = notice
    await _safe_edit_text(callback, text, get_admin_user_actions_keyboard(telegram_id))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:sub:deactivate:"))
async def cb_admin_sub_deactivate(callback: CallbackQuery) -> None:
    """Деактивирует подписку пользователя."""
    if not _guard(callback):
        await callback.answer(ADMIN_DENIED, show_alert=True)
        return

    telegram_id = int(callback.data.split(":")[-1])
    logger.info("Admin deactivate subscription: admin={} user={}", callback.from_user.id, telegram_id)
    result = admin_repository.deactivate_user_subscription(telegram_id)

    if result is None:
        await callback.answer(ADMIN_SUB_NO_SUB, show_alert=True)
        return

    notice = ADMIN_SUB_DEACTIVATED.format(telegram_id=telegram_id)
    text = _render_user_detail(telegram_id)
    if text is not None:
        text = f"{notice}\n\n{text}"
    else:
        text = notice
    await _safe_edit_text(callback, text, get_admin_user_actions_keyboard(telegram_id))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:sub:extend:"))
async def cb_admin_sub_extend(callback: CallbackQuery) -> None:
    """Продлевает подписку пользователя."""
    if not _guard(callback):
        await callback.answer(ADMIN_DENIED, show_alert=True)
        return

    parts = callback.data.split(":")
    telegram_id = int(parts[3])
    extra_days = int(parts[4])
    logger.info("Admin extend subscription: admin={} user={} days={}", callback.from_user.id, telegram_id, extra_days)

    result = admin_repository.extend_user_subscription(telegram_id, extra_days)
    if result is None:
        await callback.answer(ADMIN_SUB_NO_SUB, show_alert=True)
        return

    notice = ADMIN_SUB_EXTENDED.format(days=extra_days, telegram_id=telegram_id)
    text = _render_user_detail(telegram_id)
    if text is not None:
        text = f"{notice}\n\n{text}"
    else:
        text = notice
    await _safe_edit_text(callback, text, get_admin_user_actions_keyboard(telegram_id))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:sub:shrink:"))
async def cb_admin_sub_shrink(callback: CallbackQuery) -> None:
    """Уменьшает срок подписки пользователя."""
    if not _guard(callback):
        await callback.answer(ADMIN_DENIED, show_alert=True)
        return

    parts = callback.data.split(":")
    telegram_id = int(parts[3])
    reduce_days = int(parts[4])
    logger.info("Admin shrink subscription: admin={} user={} days={}", callback.from_user.id, telegram_id, reduce_days)

    result = admin_repository.shrink_user_subscription(telegram_id, reduce_days)

    # unlimited subscription — cannot shrink, inform admin
    if result is not None and result.expires_at is None:
        await callback.answer("♾️ У пользователя бессрочная подписка — уменьшение недоступно", show_alert=True)
        return

    if result is None:
        await callback.answer(ADMIN_SUB_NO_SUB, show_alert=True)
        return

    notice = ADMIN_SUB_SHRUNK.format(days=reduce_days, telegram_id=telegram_id)
    text = _render_user_detail(telegram_id)
    if text is not None:
        text = f"{notice}\n\n{text}"
    else:
        text = notice
    await _safe_edit_text(callback, text, get_admin_user_actions_keyboard(telegram_id))
    await callback.answer()


# ── Управление токенами ────────────────────────────────────


@router.callback_query(F.data.startswith("admin:tokens:add:"))
async def cb_admin_tokens_add(callback: CallbackQuery) -> None:
    """Добавляет токены пользователю."""
    if not _guard(callback):
        await callback.answer(ADMIN_DENIED, show_alert=True)
        return

    parts = callback.data.split(":")
    telegram_id = int(parts[3])
    count = int(parts[4])
    logger.info("Admin add tokens: admin={} user={} count={}", callback.from_user.id, telegram_id, count)

    payment_repository.add_tokens(telegram_id, count)

    notice = ADMIN_TOKENS_ADDED.format(count=count, telegram_id=telegram_id)
    text = _render_user_detail(telegram_id)
    if text is not None:
        text = f"{notice}\n\n{text}"
    else:
        text = notice
    await _safe_edit_text(callback, text, get_admin_user_actions_keyboard(telegram_id))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:tokens:remove:"))
async def cb_admin_tokens_remove(callback: CallbackQuery) -> None:
    """Убирает токены у пользователя."""
    if not _guard(callback):
        await callback.answer(ADMIN_DENIED, show_alert=True)
        return

    parts = callback.data.split(":")
    telegram_id = int(parts[3])
    count = int(parts[4])
    logger.info("Admin remove tokens: admin={} user={} count={}", callback.from_user.id, telegram_id, count)

    subscription = payment_repository.get_subscription(telegram_id)
    if subscription is None:
        await callback.answer(ADMIN_SUB_NO_SUB, show_alert=True)
        return

    current_tokens = subscription.tokens
    new_tokens = max(0, current_tokens - count)
    payment_repository.upsert_subscription(
        telegram_id=telegram_id,
        status=subscription.status,
        expires_at=subscription.expires_at,
        transaction_id=subscription.transaction_id or "admin_token_remove",
        tokens=new_tokens,
    )

    notice = ADMIN_TOKENS_REMOVED.format(count=min(count, current_tokens), telegram_id=telegram_id)
    text = _render_user_detail(telegram_id)
    if text is not None:
        text = f"{notice}\n\n{text}"
    else:
        text = notice
    await _safe_edit_text(callback, text, get_admin_user_actions_keyboard(telegram_id))
    await callback.answer()


# ── Статистика ────────────────────────────────────────────


@router.callback_query(F.data == "admin:stats")
async def cb_admin_stats(callback: CallbackQuery) -> None:
    """Показывает общую статистику и клавиатуру графиков."""
    if not _guard(callback):
        await callback.answer(ADMIN_DENIED, show_alert=True)
        return

    stats = admin_repository.get_overall_stats()
    text = f"{ADMIN_STATS_TITLE}\n\n{format_admin_stats(stats)}"
    await _safe_edit_text(callback, text, get_admin_stats_keyboard())
    await callback.answer()


# ── Графики ───────────────────────────────────────────────


@router.callback_query(F.data == "admin:chart:daily")
async def cb_admin_chart_daily(callback: CallbackQuery) -> None:
    """Отправляет график ежедневной активности."""
    if not _guard(callback):
        await callback.answer(ADMIN_DENIED, show_alert=True)
        return

    buf = generate_daily_usage_chart(days=30)
    photo = BufferedInputFile(buf.read(), filename="daily_usage.png")
    if callback.message is not None:
        await callback.message.answer_photo(
            photo, caption="📈 Ежедневная активность (30 дней)", parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data == "admin:chart:monthly")
async def cb_admin_chart_monthly(callback: CallbackQuery) -> None:
    """Отправляет график помесячной активности."""
    if not _guard(callback):
        await callback.answer(ADMIN_DENIED, show_alert=True)
        return

    buf = generate_monthly_usage_chart(months=12)
    photo = BufferedInputFile(buf.read(), filename="monthly_usage.png")
    if callback.message is not None:
        await callback.message.answer_photo(
            photo, caption="📈 Помесячная активность (12 месяцев)", parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data == "admin:chart:subs")
async def cb_admin_chart_subs(callback: CallbackQuery) -> None:
    """Отправляет круговую диаграмму подписок."""
    if not _guard(callback):
        await callback.answer(ADMIN_DENIED, show_alert=True)
        return

    buf = generate_subscription_chart()
    photo = BufferedInputFile(buf.read(), filename="subscriptions.png")
    if callback.message is not None:
        await callback.message.answer_photo(
            photo, caption="🥧 Подписки: активные / неактивные", parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data == "admin:chart:revenue")
async def cb_admin_chart_revenue(callback: CallbackQuery) -> None:
    """Отправляет график выручки."""
    if not _guard(callback):
        await callback.answer(ADMIN_DENIED, show_alert=True)
        return

    buf = generate_revenue_chart(days=30)
    photo = BufferedInputFile(buf.read(), filename="revenue.png")
    if callback.message is not None:
        await callback.message.answer_photo(
            photo, caption="💰 Выручка за 30 дней", parse_mode="HTML"
        )
    await callback.answer()
