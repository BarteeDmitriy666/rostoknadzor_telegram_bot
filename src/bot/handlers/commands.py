"""Обработчики команд с главным меню."""
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.filters.command import CommandObject
from loguru import logger

from src.bot.formatters import (
    format_crops_list,
    format_help_message,
    format_regions_list,
    format_start_message,
)
from src.bot.keyboards import (
    get_crops_list_keyboard,
    get_main_reply_keyboard,
    get_regions_list_keyboard,
)
from src.bot.handlers.prediction import show_user_forecasts, start_predict_flow
from src.bot.handlers.subscription import (
    _send_monthly_payment_link,
    _send_token_payment_link,
    send_subscription_prompt,
)
from src.bot.localization import START_PURCHASE_MONTHLY, START_PURCHASE_TOKENS
from src.core.config import settings
from src.db.connection import get_or_create_user
from src.payments.subscription import is_subscribed

router = Router(name="commands")


def _parse_deep_link(args: str | None) -> tuple[str, int]:
    """Parse /start deep link parameter.

    Returns (action, quantity):
      - ("monthly", days) for "monthly_N" (e.g. monthly_30 → 30 days)
      - ("monthly", 0) for "monthly" (show tier selection)
      - ("tokens", 0) for "tokens" (show count selection)
      - ("tokens", N) for "tokens_N" (direct N-token purchase)
      - ("", 0) for no deep link
    """
    if not args:
        return ("", 0)

    args = args.strip().lower()

    if args == "monthly":
        return ("monthly", 0)

    if args.startswith("monthly_"):
        try:
            days = int(args.split("_")[1])
            if days > 0:
                return ("monthly", days)
        except (ValueError, IndexError):
            pass
        return ("monthly", 0)

    if args == "tokens":
        return ("tokens", 0)

    if args.startswith("tokens_"):
        try:
            count = int(args.split("_")[1])
            if count > 0:
                return ("tokens", count)
        except (ValueError, IndexError):
            pass
        return ("tokens", 0)

    return ("", 0)


@router.message(CommandStart(deep_link=True))
async def cmd_start_deep(message: Message, command: CommandObject) -> None:
    """Обрабатывает /start с deep-link параметром — прямой переход к оплате."""
    if message.from_user is None:
        return

    telegram_id = message.from_user.id

    # Регистрируем пользователя при первом контакте
    get_or_create_user(
        telegram_id=telegram_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    action, quantity = _parse_deep_link(command.args)
    logger.info("Deep link start: user={} action={} quantity={}", telegram_id, action, quantity)

    # Already subscribed — show info and main menu
    if is_subscribed(telegram_id):
        await message.answer(
            format_start_message(),
            parse_mode="HTML",
            reply_markup=get_main_reply_keyboard(),
        )
        return

    if action == "monthly":
        if quantity > 0:
            # Direct tier link (e.g. /start monthly_30)
            duration_days = quantity
        else:
            # No specific tier — show tier selection
            await send_subscription_prompt(message, telegram_id)
            return
        price = int(settings.SUBSCRIPTION_TIERS.get(duration_days, min(settings.SUBSCRIPTION_TIERS.values())))
        logger.info("Sending monthly payment link: user={} days={}", telegram_id, duration_days)
        await message.answer(
            START_PURCHASE_MONTHLY.format(price=price),
            parse_mode="HTML",
        )
        await _send_monthly_payment_link(message, telegram_id, duration_days)

    elif action == "tokens":
        if quantity > 0:
            logger.info("Sending token payment link: user={} count={}", telegram_id, quantity)
            await message.answer(
                START_PURCHASE_TOKENS.format(count=quantity),
                parse_mode="HTML",
            )
            await _send_token_payment_link(message, telegram_id, quantity)
        else:
            # No specific count — show token count selection
            await send_subscription_prompt(message, telegram_id)
    else:
        # Unknown deep link — fall through to normal start
        await message.answer(
            format_start_message(),
            parse_mode="HTML",
            reply_markup=get_main_reply_keyboard(),
        )


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Обрабатывает команду /start без параметра — показывает главное меню."""
    if message.from_user is not None:
        # Регистрируем пользователя при первом контакте
        user = get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        logger.info("User registered: id={} username={}", message.from_user.id, message.from_user.username)

    await message.answer(
        format_start_message(),
        parse_mode="HTML",
        reply_markup=get_main_reply_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Обрабатывает команду /help."""
    logger.debug("Help command from user={}", message.from_user.id if message.from_user else None)
    await message.answer(format_help_message(), parse_mode="HTML")


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    """Обрабатывает команду /menu - показывает главное меню."""
    await message.answer(
        format_start_message(),
        parse_mode="HTML",
        reply_markup=get_main_reply_keyboard(),
    )


@router.message(Command("crops"))
async def cmd_crops(message: Message) -> None:
    """Обрабатывает команду /crops."""
    await message.answer(
        format_crops_list(),
        parse_mode="HTML",
        reply_markup=get_crops_list_keyboard(),
    )


@router.message(Command("regions"))
async def cmd_regions(message: Message) -> None:
    """Обрабатывает команду /regions."""
    await message.answer(
        format_regions_list(),
        parse_mode="HTML",
        reply_markup=get_regions_list_keyboard(),
    )


@router.message(Command("myforecasts"))
async def cmd_myforecasts(message: Message, state: FSMContext) -> None:
    """Обрабатывает команду /myforecasts."""
    if message.from_user is None:
        await message.answer("Команда недоступна в группах.", parse_mode="HTML")
        return
    await show_user_forecasts(message, message.from_user.id, state)


@router.message(Command("predict"))
async def cmd_predict(message: Message, state: FSMContext) -> None:
    """Обрабатывает команду /predict."""
    if message.from_user is None:
        return
    if not is_subscribed(message.from_user.id):
        logger.info("Predict denied: user={} not subscribed", message.from_user.id)
        await send_subscription_prompt(message, message.from_user.id)
        return
    logger.info("Predict started: user={}", message.from_user.id)
    await start_predict_flow(message, state)


@router.message(F.text == "🌾 Новый прогноз")
async def btn_new_forecast(message: Message, state: FSMContext) -> None:
    """Обрабатывает кнопку 'Новый прогноз'."""
    if message.from_user is None:
        return
    if not is_subscribed(message.from_user.id):
        await send_subscription_prompt(message, message.from_user.id)
        return
    await start_predict_flow(message, state)


@router.message(F.text == "📋 Мои прогнозы")
async def btn_my_forecasts(message: Message, state: FSMContext) -> None:
    """Обрабатывает кнопку 'Мои прогнозы'."""
    if message.from_user is None:
        await message.answer("Команда недоступна в группах.", parse_mode="HTML")
        return
    await show_user_forecasts(message, message.from_user.id, state)


@router.message(F.text == "🌻 О культурах")
async def btn_crops(message: Message) -> None:
    """Обрабатывает кнопку 'О культурах'."""
    await message.answer(
        format_crops_list(),
        parse_mode="HTML",
        reply_markup=get_crops_list_keyboard(),
    )


@router.message(F.text == "🗺️ О регионах")
async def btn_regions(message: Message) -> None:
    """Обрабатывает кнопку 'О регионах'."""
    await message.answer(
        format_regions_list(),
        parse_mode="HTML",
        reply_markup=get_regions_list_keyboard(),
    )


@router.message(F.text == "❓ Помощь")
async def btn_help(message: Message) -> None:
    """Обрабатывает кнопку 'Помощь'."""
    await message.answer(format_help_message(), parse_mode="HTML")
