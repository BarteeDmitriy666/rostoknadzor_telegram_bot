"""Тесты для репозитория прогнозов."""
import json
from datetime import datetime

import pytest
from peewee import SqliteDatabase

from src.db.forecast_repository import (
    delete_forecast,
    get_forecast_by_id,
    get_forecasts_count,
    get_user_forecasts,
    save_forecast,
)
from src.db.models import Forecast, User
from src.ml.dataset.schemas import AgriculturalZone, CropType, RiskLevel


@pytest.fixture
def setup_db():
    """Настройка тестовой базы данных."""
    test_db = SqliteDatabase(":memory:")
    User._meta.database = test_db
    Forecast._meta.database = test_db
    
    test_db.create_tables([User, Forecast], safe=True)
    
    # Создаём тестового пользователя
    user = User.create(
        telegram_id=12345,
        username="testuser",
    )
    
    yield user, test_db
    
    test_db.drop_tables([User, Forecast])
    test_db.close()


def test_save_forecast(setup_db):
    """Тест сохранения прогноза."""
    user, test_db = setup_db
    
    monthly_risk = {"May": RiskLevel.GREEN, "June": RiskLevel.YELLOW}
    stages_data = [{"stage": "sowing", "date": "2024-04-01"}]
    
    forecast = save_forecast(
        user=user,
        zone=AgriculturalZone.SOUTH,
        crop=CropType.WINTER_WHEAT,
        sowing_date=datetime(2024, 4, 1),
        harvest_date=datetime(2024, 7, 15),
        yield_forecast=45.5,
        overall_risk=RiskLevel.GREEN,
        monthly_risk=monthly_risk,
        stages_data=stages_data,
    )
    
    assert forecast.id is not None
    assert forecast.zone == "south"
    assert forecast.zone_display == "Юг"
    assert forecast.crop == "winter_wheat"
    assert forecast.crop_display == "Озимая пшеница"
    assert forecast.yield_forecast == 45.5
    assert forecast.overall_risk == "green"


def test_get_user_forecasts(setup_db):
    """Тест получения прогнозов пользователя."""
    user, test_db = setup_db
    
    # Создаём несколько прогнозов
    for i in range(5):
        Forecast.create(
            user=user,
            zone="south",
            zone_display="Юг",
            crop="winter_wheat",
            crop_display="Озимая пшеница",
            sowing_date=datetime(2024, 4, 1),
            harvest_date=datetime(2024, 7, 15),
            yield_forecast=40.0 + i,
            overall_risk="green",
            monthly_risk_json=json.dumps({}),
            stages_json=json.dumps([]),
        )
    
    forecasts = get_user_forecasts(user, limit=3)
    
    assert len(forecasts) == 3
    # Должны быть упорядочены по created_at desc (новые first)
    assert forecasts[0].yield_forecast >= forecasts[1].yield_forecast


def test_get_user_forecasts_pagination(setup_db):
    """Тест пагинации прогнозов."""
    user, test_db = setup_db
    
    # Создаём 10 прогнозов
    for i in range(10):
        Forecast.create(
            user=user,
            zone="south",
            zone_display="Юг",
            crop="winter_wheat",
            crop_display="Озимая пшеница",
            sowing_date=datetime(2024, 4, 1),
            harvest_date=datetime(2024, 7, 15),
            yield_forecast=40.0 + i,
            overall_risk="green",
            monthly_risk_json=json.dumps({}),
            stages_json=json.dumps([]),
        )
    
    # Первая страница
    page1 = get_user_forecasts(user, limit=5, offset=0)
    assert len(page1) == 5
    
    # Вторая страница
    page2 = get_user_forecasts(user, limit=5, offset=5)
    assert len(page2) == 5
    
    # Третья страница (должна быть пустой)
    page3 = get_user_forecasts(user, limit=5, offset=10)
    assert len(page3) == 0


def test_get_forecast_by_id_existing(setup_db):
    """Тест получения прогноза по ID."""
    user, test_db = setup_db
    
    forecast = Forecast.create(
        user=user,
        zone="south",
        zone_display="Юг",
        crop="corn",
        crop_display="Кукуруза",
        sowing_date=datetime(2024, 5, 1),
        harvest_date=datetime(2024, 9, 1),
        yield_forecast=80.0,
        overall_risk="yellow",
        monthly_risk_json=json.dumps({}),
        stages_json=json.dumps([]),
    )
    
    result = get_forecast_by_id(forecast.id)
    
    assert result is not None
    assert result.id == forecast.id
    assert result.crop == "corn"


def test_get_forecast_by_id_not_found(setup_db):
    """Тест получения несуществующего прогноза."""
    user, test_db = setup_db
    
    result = get_forecast_by_id(99999)
    
    assert result is None


def test_delete_forecast_existing(setup_db):
    """Тест удаления существующего прогноза."""
    user, test_db = setup_db
    
    forecast = Forecast.create(
        user=user,
        zone="south",
        zone_display="Юг",
        crop="corn",
        crop_display="Кукуруза",
        sowing_date=datetime(2024, 5, 1),
        harvest_date=datetime(2024, 9, 1),
        yield_forecast=80.0,
        overall_risk="yellow",
        monthly_risk_json=json.dumps({}),
        stages_json=json.dumps([]),
    )
    
    forecast_id = forecast.id
    
    result = delete_forecast(forecast_id)
    
    assert result is True
    assert get_forecast_by_id(forecast_id) is None


def test_delete_forecast_not_found(setup_db):
    """Тест удаления несуществующего прогноза."""
    user, test_db = setup_db
    
    result = delete_forecast(99999)
    
    assert result is False


def test_get_forecasts_count(setup_db):
    """Тест получения количества прогнозов."""
    user, test_db = setup_db
    
    assert get_forecasts_count(user) == 0
    
    # Добавляем прогнозы
    for i in range(3):
        Forecast.create(
            user=user,
            zone="south",
            zone_display="Юг",
            crop="winter_wheat",
            crop_display="Озимая пшеница",
            sowing_date=datetime(2024, 4, 1),
            harvest_date=datetime(2024, 7, 15),
            yield_forecast=40.0,
            overall_risk="green",
            monthly_risk_json=json.dumps({}),
            stages_json=json.dumps([]),
        )
    
    assert get_forecasts_count(user) == 3
