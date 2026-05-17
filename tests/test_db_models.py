"""Тесты для моделей базы данных."""
import json
from datetime import datetime

import pytest
from peewee import SqliteDatabase


@pytest.fixture
def setup_db():
    """Настройка тестовой базы данных."""
    # Создаём тестовую базу данных
    test_db = SqliteDatabase(":memory:")
    
    # Импортируем и патчим
    from src.db import models
    original_db = models.database
    
    # Привязываем тестовую базу данных к моделям
    models.database = test_db
    
    # Создаём экземпляры с тестовой базой данных
    from src.db.models import User, Forecast
    User._meta.database = test_db
    Forecast._meta.database = test_db
    
    # Создаём таблицы
    test_db.create_tables([User, Forecast], safe=True)
    
    yield test_db
    
    # Очистка
    test_db.drop_tables([User, Forecast], safe=True)
    test_db.close()
    models.database = original_db


def test_user_creation(setup_db):
    """Тест создания пользователя."""
    from src.db.models import User
    
    user = User.create(
        telegram_id=12345,
        username="testuser",
        first_name="Test",
        last_name="User",
    )
    
    assert user.telegram_id == 12345
    assert user.username == "testuser"
    assert user.first_name == "Test"
    assert user.last_name == "User"
    assert user.language_code == "ru"


def test_user_unique_telegram_id(setup_db):
    """Тест уникальности telegram_id."""
    from src.db.models import User
    
    User.create(telegram_id=12345, username="user1")
    
    with pytest.raises(Exception):
        User.create(telegram_id=12345, username="user2")


def test_forecast_creation(setup_db):
    """Тест создания прогноза."""
    from src.db.models import User, Forecast
    
    user = User.create(telegram_id=12345, username="testuser")
    
    forecast = Forecast.create(
        user=user,
        zone="south",
        zone_display="Юг",
        crop="winter_wheat",
        crop_display="Озимая пшеница",
        sowing_date=datetime(2024, 4, 1),
        harvest_date=datetime(2024, 7, 15),
        yield_forecast=45.5,
        overall_risk="green",
        monthly_risk_json=json.dumps({"May": "green", "June": "yellow"}),
        stages_json=json.dumps([{"stage": "sowing", "date": "2024-04-01"}]),
    )
    
    assert forecast.user == user
    assert forecast.zone == "south"
    assert forecast.yield_forecast == 45.5
    assert forecast.overall_risk == "green"


def test_forecast_get_monthly_risk(setup_db):
    """Тест получения месячного риска из прогноза."""
    from src.db.models import User, Forecast
    
    user = User.create(telegram_id=12345, username="testuser")
    
    monthly_risk_data = {
        "April": "green",
        "May": "yellow",
        "June": "red",
    }
    
    forecast = Forecast.create(
        user=user,
        zone="south",
        zone_display="Юг",
        crop="winter_wheat",
        crop_display="Озимая пшеница",
        sowing_date=datetime(2024, 4, 1),
        harvest_date=datetime(2024, 7, 15),
        yield_forecast=45.5,
        overall_risk="yellow",
        monthly_risk_json=json.dumps(monthly_risk_data),
        stages_json=json.dumps([]),
    )
    
    result = forecast.get_monthly_risk()
    
    assert result == monthly_risk_data
    assert result["April"] == "green"
    assert result["May"] == "yellow"
    assert result["June"] == "red"


def test_forecast_get_stages(setup_db):
    """Тест получения стадий из прогноза."""
    from src.db.models import User, Forecast
    
    user = User.create(telegram_id=12345, username="testuser")
    
    stages_data = [
        {"stage": "sowing", "date": "2024-04-01"},
        {"stage": "emergence", "date": "2024-04-15"},
    ]
    
    forecast = Forecast.create(
        user=user,
        zone="south",
        zone_display="Юг",
        crop="winter_wheat",
        crop_display="Озимая пшеница",
        sowing_date=datetime(2024, 4, 1),
        harvest_date=datetime(2024, 7, 15),
        yield_forecast=45.5,
        overall_risk="green",
        monthly_risk_json=json.dumps({}),
        stages_json=json.dumps(stages_data),
    )
    
    result = forecast.get_stages()
    
    assert len(result) == 2
    assert result[0]["stage"] == "sowing"
    assert result[1]["stage"] == "emergence"


def test_user_forecasts_relationship(setup_db):
    """Тест связи пользователь-прогнозы."""
    from src.db.models import User, Forecast
    
    user = User.create(telegram_id=12345, username="testuser")
    
    # Создаём несколько прогнозов
    for i in range(3):
        Forecast.create(
            user=user,
            zone="south",
            zone_display="Юг",
            crop="winter_wheat",
            crop_display="Озимая пшеница",
            sowing_date=datetime(2024, 4, 1),
            harvest_date=datetime(2024, 7, 15),
            yield_forecast=45.5 + i,
            overall_risk="green",
            monthly_risk_json=json.dumps({}),
            stages_json=json.dumps([]),
        )
    
    assert user.forecasts.count() == 3
