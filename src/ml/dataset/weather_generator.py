"""Генератор погоды на основе зоны и даты."""
import random
from datetime import datetime, timedelta

import numpy as np

from src.ml.dataset.schemas import AgriculturalZone, WeatherInput


# Климатические характеристики по зонам
ZONE_CLIMATE = {
    AgriculturalZone.NORTHWEST: {
        "temp_mean": 8.5,
        "temp_amplitude": 25,
        "humidity_mean": 65,
        "humidity_std": 15,
        "precip_mean": 45,
        "precip_std": 20,
    },
    AgriculturalZone.NORTHEAST: {
        "temp_mean": 9.0,
        "temp_amplitude": 28,
        "humidity_mean": 58,
        "humidity_std": 18,
        "precip_mean": 40,
        "precip_std": 18,
    },
    AgriculturalZone.CENTRAL_IRRIGATED: {
        "temp_mean": 10.0,
        "temp_amplitude": 22,
        "humidity_mean": 62,
        "humidity_std": 14,
        "precip_mean": 50,
        "precip_std": 22,
    },
    AgriculturalZone.AZOV: {
        "temp_mean": 11.5,
        "temp_amplitude": 20,
        "humidity_mean": 70,
        "humidity_std": 12,
        "precip_mean": 55,
        "precip_std": 25,
    },
    AgriculturalZone.SOUTH: {
        "temp_mean": 12.0,
        "temp_amplitude": 18,
        "humidity_mean": 68,
        "humidity_std": 13,
        "precip_mean": 52,
        "precip_std": 23,
    },
    AgriculturalZone.EAST: {
        "temp_mean": 10.5,
        "temp_amplitude": 30,
        "humidity_mean": 52,
        "humidity_std": 20,
        "precip_mean": 35,
        "precip_std": 15,
    },
}


def generate_weather(zone: AgriculturalZone, date: datetime, seed: int | None = None) -> WeatherInput:
    """
    Генерирует погоду для конкретной зоны и даты.
    
    Использует синусоидальные паттерны для температуры (сезонные) и 
    экспоненциальное распределение для осадков.
    
    Args:
        zone: Сельскохозяйственная зона
        date: Дата для генерации погоды
        seed: Опциональное зерно случайности для воспроизводимости
    
    Returns:
        WeatherInput с температурой, влажностью, осадками
    """
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)
    
    climate = ZONE_CLIMATE[zone]
    day_of_year = date.timetuple().tm_yday
    
    # Температура: синусоидальный паттерн со средним и амплитудой для зоны
    # Пик около 180 дня (июль), минимум около 0 дня (январь)
    temp = (
        climate["temp_mean"]
        + climate["temp_amplitude"] / 2 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
    )
    # Добавляем дневную вариацию
    temp += np.random.normal(0, 3)
    temp = round(max(-15, min(45, temp)), 1)
    
    # Влажность: несколько обратно коррелирует с температурой
    humidity = climate["humidity_mean"] - (temp - climate["temp_mean"]) * 0.5
    humidity += np.random.normal(0, climate["humidity_std"])
    humidity = min(100, max(20, round(humidity, 1)))
    
    # Осадки: экспоненциальное распределение с редкими дождями
    # Высокая вероятность дождя весной/осенью
    season_factor = 1.0 + 0.3 * np.cos(2 * np.pi * (day_of_year - 100) / 365)
    precip = np.random.exponential(climate["precip_mean"] * season_factor / 10)
    precip = round(min(100, max(0, precip)), 1)
    
    return WeatherInput(
        temperature=temp,
        humidity=humidity,
        precipitation=precip,
    )


def generate_weather_series(
    zone: AgriculturalZone,
    start_date: datetime,
    end_date: datetime,
    interval_days: int = 7,
) -> list[tuple[datetime, WeatherInput]]:
    """
    Генерирует ряд погоды для диапазона дат.
    
    Args:
        zone: Сельскохозяйственная зона
        start_date: Дата начала
        end_date: Дата окончания
        interval_days: Дни между измерениями
    
    Returns:
        Список кортежей (дата, погода)
    """
    result = []
    current_date = start_date
    day_count = 0
    
    while current_date <= end_date:
        weather = generate_weather(zone, current_date, seed=day_count)
        result.append((current_date, weather))
        current_date = current_date + timedelta(days=interval_days)
        day_count += 1
    
    return result