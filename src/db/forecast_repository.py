"""Репозиторий для операций с прогнозами в базе данных."""
import json
from datetime import datetime

from loguru import logger

from src.bot.formatters import format_crop_display, format_zone_display
from src.db.models import Forecast, User
from src.ml.dataset.schemas import AgriculturalZone, CropType, RiskLevel


def save_forecast(
    user: User,
    zone: AgriculturalZone,
    crop: CropType,
    sowing_date: datetime,
    harvest_date: datetime,
    yield_forecast: float,
    overall_risk: RiskLevel,
    monthly_risk: dict,
    stages_data: list,
) -> Forecast:
    """Сохраняет прогноз в базу данных."""
    forecast = Forecast.create(
        user=user,
        zone=zone.value,
        zone_display=format_zone_display(zone),
        crop=crop.value,
        crop_display=format_crop_display(crop),
        sowing_date=sowing_date,
        harvest_date=harvest_date,
        yield_forecast=yield_forecast,
        overall_risk=overall_risk.value,
        monthly_risk_json=json.dumps(monthly_risk),
        stages_json=json.dumps(stages_data),
    )
    logger.info("Forecast saved: id={} user={} zone={} crop={}", forecast.id, user.telegram_id, zone.value, crop.value)
    return forecast


def get_user_forecasts(
    user: User,
    limit: int = 10,
    offset: int = 0,
) -> list[Forecast]:
    """Возвращает прогнозы пользователя с пагинацией."""
    return (
        Forecast.select()
        .where(Forecast.user == user)
        .order_by(Forecast.created_at.desc())
        .limit(limit)
        .offset(offset)
    )


def get_forecast_by_id(forecast_id: int) -> Forecast | None:
    """Возвращает прогноз по ID."""
    try:
        return Forecast.get_by_id(forecast_id)
    except Forecast.DoesNotExist:
        return None


def delete_forecast(forecast_id: int) -> bool:
    """Удаляет прогноз по ID."""
    try:
        forecast = Forecast.get_by_id(forecast_id)
        forecast.delete_instance()
        logger.info("Forecast deleted: id={}", forecast_id)
        return True
    except Forecast.DoesNotExist:
        logger.warning("Forecast delete failed: id={} not found", forecast_id)
        return False


def get_forecasts_count(user: User) -> int:
    """Возвращает общее количество прогнозов для пользователя."""
    return Forecast.select().where(Forecast.user == user).count()
