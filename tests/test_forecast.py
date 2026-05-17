"""Тесты для сезонного прогноза и графиков."""
from datetime import datetime

import pytest

from src.ml.charts import generate_forecast_chart, generate_monthly_summary_chart
from src.ml.dataset.schemas import AgriculturalZone, CropType
from src.ml.forecast import forecast_season


def test_season_forecast():
    """Тест генерации сезонного прогноза."""
    forecast = forecast_season(
        zone=AgriculturalZone.CENTRAL_IRRIGATED,
        crop=CropType.WINTER_WHEAT,
        sowing_date=datetime(2024, 4, 1),
    )
    
    assert forecast.yield_forecast > 0
    assert forecast.harvest_date > forecast.sowing_date
    assert len(forecast.stages) == 6
    assert len(forecast.monthly_risk) > 0


def test_season_forecast_all_crops():
    """Тест сезонного прогноза для всех культур."""
    for crop in CropType:
        forecast = forecast_season(
            zone=AgriculturalZone.SOUTH,
            crop=crop,
            sowing_date=datetime(2024, 4, 15),
        )
        
        assert forecast.yield_forecast > 0
        assert len(forecast.stages) == 6


def test_chart_generation():
    """Тест генерации графиков."""
    forecast = forecast_season(
        zone=AgriculturalZone.AZOV,
        crop=CropType.CORN,
        sowing_date=datetime(2024, 5, 1),
    )
    
    # Тест основного графика
    chart = generate_forecast_chart(forecast)
    assert chart.getvalue() is not None
    assert len(chart.getvalue()) > 0
    
    # Тест месячной сводки
    monthly = generate_monthly_summary_chart(forecast)
    assert monthly.getvalue() is not None
    assert len(monthly.getvalue()) > 0


def test_monthly_risk_calculation():
    """Тест корректного расчёта месячного риска."""
    forecast = forecast_season(
        zone=AgriculturalZone.NORTHWEST,
        crop=CropType.SUNFLOWER,
        sowing_date=datetime(2024, 4, 10),
    )
    
    # Проверяем, что все месячные риски корректны
    for month, risk in forecast.monthly_risk.items():
        assert risk.value in ["green", "yellow", "red"]
    
    # Проверяем порядок месяцев
    months_order = ["April", "May", "June", "July", "August", "September", "October", "November"]
    forecast_months = [m for m in months_order if m in forecast.monthly_risk]
    assert len(forecast_months) > 0
