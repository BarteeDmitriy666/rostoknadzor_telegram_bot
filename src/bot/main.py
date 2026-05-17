"""Точка входа бота."""
import asyncio
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from src.bot.formatters import format_cancel_message
from src.bot.handlers import commands_router, prediction_router, subscription_router, admin_router
from src.bot.keyboards import get_main_reply_keyboard
from src.core.config import settings
from src.db import init_database, close_database
from src.webapp.main import app, run_webhook_server


async def main() -> None:
    """Запускает бота и вебхук сервер."""
    # Убеждаемся, что директория для логов существует
    Path("logs").mkdir(exist_ok=True)
    
    # Настраиваем логирование
    logger.add(
        "logs/bot.log",
        rotation="10 MB",
        retention="7 days",
        level=settings.log_level,
    )
    
    # Проверяем токен бота
    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN не установлен в переменных окружения или .env файле")
        sys.exit(1)
    
    # Инициализируем базу данных
    logger.info("Инициализация базы данных...")
    init_database()
    logger.info("База данных инициализирована")
    
    # Инициализируем бота и диспетчера
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    
    # Подключаем роутеры
    dp.include_router(commands_router)
    dp.include_router(prediction_router)
    dp.include_router(subscription_router)
    dp.include_router(admin_router)

    # Передаём бот в вебхук-сервер для отправки уведомлений
    app.state.bot = bot
    
    # Глобальный обработчик отмены
    @dp.message(Command("cancel"))
    async def global_cancel(message: Message, state: FSMContext) -> None:
        """Глобально отменяет разговор."""
        await state.clear()
        await message.answer(
            format_cancel_message(),
            parse_mode="HTML",
            reply_markup=get_main_reply_keyboard(),
        )
    
    logger.info("Запуск бота...")

    # Запускаем вебхук сервер и бота параллельно
    try:
        await asyncio.gather(
            dp.start_polling(bot),
            run_webhook_server(),
        )
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        await bot.session.close()
        close_database()
        logger.info("Database closed")


if __name__ == "__main__":
    asyncio.run(main())