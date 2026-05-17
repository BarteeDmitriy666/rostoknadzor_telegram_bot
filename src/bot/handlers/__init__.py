"""Пакет обработчиков бота."""
from src.bot.handlers.admin import router as admin_router
from src.bot.handlers.commands import router as commands_router
from src.bot.handlers.prediction import router as prediction_router
from src.bot.handlers.subscription import router as subscription_router

__all__ = ["commands_router", "prediction_router", "subscription_router", "admin_router"]
