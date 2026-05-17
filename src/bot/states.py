"""Состояния FSM бота для потока разговора."""
from aiogram.fsm.state import State, StatesGroup


class PredictionStates(StatesGroup):
    """Состояния для разговора предсказания - упрощённый поток."""
    waiting_for_zone = State()
    waiting_for_crop = State()
    waiting_for_date = State()


class SubscriptionStates(StatesGroup):
    """Состояния для покупки подписки."""
    selecting_token_count = State()


class AdminStates(StatesGroup):
    """Состояния для админ-панели."""
    viewing_users = State()
    viewing_user_detail = State()
    viewing_stats = State()
    waiting_for_user_id = State()
