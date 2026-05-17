"""Генератор синтетических данных для обучения ML."""
import random
from typing import Generator

import numpy as np
import pandas as pd

from src.ml.dataset.schemas import (
    AgriculturalZone,
    CropType,
    GrowingStage,
    TrainingRecord,
)


# Климатические характеристики по зонам
ZONE_PARAMS = {
    AgriculturalZone.NORTHWEST: {
        "temp_mean": 8.5,
        "temp_std": 6.0,
        "humidity_mean": 65,
        "precip_mean": 45,
        "yield_multiplier": 0.9,
    },
    AgriculturalZone.NORTHEAST: {
        "temp_mean": 9.0,
        "temp_std": 7.0,
        "humidity_mean": 58,
        "precip_mean": 40,
        "yield_multiplier": 0.85,
    },
    AgriculturalZone.CENTRAL_IRRIGATED: {
        "temp_mean": 10.0,
        "temp_std": 5.5,
        "humidity_mean": 62,
        "precip_mean": 50,
        "yield_multiplier": 1.15,
    },
    AgriculturalZone.AZOV: {
        "temp_mean": 11.5,
        "temp_std": 4.5,
        "humidity_mean": 70,
        "precip_mean": 55,
        "yield_multiplier": 1.0,
    },
    AgriculturalZone.SOUTH: {
        "temp_mean": 12.0,
        "temp_std": 4.0,
        "humidity_mean": 68,
        "precip_mean": 52,
        "yield_multiplier": 1.1,
    },
    AgriculturalZone.EAST: {
        "temp_mean": 10.5,
        "temp_std": 8.0,
        "humidity_mean": 52,
        "precip_mean": 35,
        "yield_multiplier": 0.8,
    },
}

# Базовые урожаи по культурам (центнеров/гектар) и характеристики
CROP_PARAMS = {
    CropType.WINTER_WHEAT: {"base_yield": 45, "drought_sensitivity": 0.7, "disease_risk": 0.4},
    CropType.SPRING_BARLEY: {"base_yield": 35, "drought_sensitivity": 0.6, "disease_risk": 0.3},
    CropType.CORN: {"base_yield": 80, "drought_sensitivity": 0.8, "disease_risk": 0.5},
    CropType.OATS: {"base_yield": 30, "drought_sensitivity": 0.4, "disease_risk": 0.35},
    CropType.RYE: {"base_yield": 28, "drought_sensitivity": 0.5, "disease_risk": 0.4},
    CropType.MILLET: {"base_yield": 18, "drought_sensitivity": 0.3, "disease_risk": 0.25},
    CropType.SORGHUM: {"base_yield": 40, "drought_sensitivity": 0.2, "disease_risk": 0.3},
    CropType.PEAS: {"base_yield": 22, "drought_sensitivity": 0.55, "disease_risk": 0.45},
    CropType.CHICKPEAS: {"base_yield": 18, "drought_sensitivity": 0.35, "disease_risk": 0.4},
    CropType.SUNFLOWER: {"base_yield": 25, "drought_sensitivity": 0.65, "disease_risk": 0.6},
    CropType.SUGAR_BEET: {"base_yield": 350, "drought_sensitivity": 0.75, "disease_risk": 0.55},
    CropType.SOYBEANS: {"base_yield": 20, "drought_sensitivity": 0.6, "disease_risk": 0.5},
    CropType.FLAX: {"base_yield": 12, "drought_sensitivity": 0.5, "disease_risk": 0.4},
    CropType.MUSTARD: {"base_yield": 14, "drought_sensitivity": 0.4, "disease_risk": 0.35},
    CropType.POTATOES: {"base_yield": 200, "drought_sensitivity": 0.7, "disease_risk": 0.65},
    CropType.TOMATOES: {"base_yield": 350, "drought_sensitivity": 0.75, "disease_risk": 0.7},
    CropType.ONIONS: {"base_yield": 280, "drought_sensitivity": 0.6, "disease_risk": 0.55},
    CropType.APPLES: {"base_yield": 150, "drought_sensitivity": 0.5, "disease_risk": 0.6},
    CropType.PLUMS: {"base_yield": 80, "drought_sensitivity": 0.45, "disease_risk": 0.5},
    CropType.GRAPES: {"base_yield": 60, "drought_sensitivity": 0.3, "disease_risk": 0.55},
}

# Множители риска заболеваний по стадиям
STAGE_RISK_MULTIPLIERS = {
    GrowingStage.SOWING: 0.3,
    GrowingStage.EMERGENCE: 0.5,
    GrowingStage.TILLERING: 0.6,
    GrowingStage.BOOTING: 0.8,
    GrowingStage.HEADING_FLOWERING: 1.0,  # Наиболее уязвимая стадия
    GrowingStage.RIPENING_MATURITY: 0.4,
}

# Оптимальные температуры по стадиям (упрощённо)
STAGE_OPTIMAL_TEMP = {
    GrowingStage.SOWING: 12,
    GrowingStage.EMERGENCE: 15,
    GrowingStage.TILLERING: 14,
    GrowingStage.BOOTING: 18,
    GrowingStage.HEADING_FLOWERING: 22,
    GrowingStage.RIPENING_MATURITY: 25,
}


def _calculate_disease_probability(
    humidity: float,
    temperature: float,
    crop_risk: float,
    stage: GrowingStage,
) -> float:
    """Рассчитывает вероятность заболевания на основе условий."""
    # Высокая влажность увеличивает риск заболеваний
    humidity_factor = min(1.0, max(0.0, (humidity - 40) / 60))
    
    # Умеренные температуры благоприятны для заболеваний
    temp_factor = 1.0 - abs(temperature - 20) / 25
    temp_factor = min(1.0, max(0.0, temp_factor))
    
    # Комбинируем факторы
    base_prob = crop_risk * STAGE_RISK_MULTIPLIERS[stage]
    prob = base_prob * (0.4 + humidity_factor * 0.4 + temp_factor * 0.2)
    
    # Добавляем случайность
    noise = np.random.normal(0, 0.05)
    prob = min(1.0, max(0.0, prob + noise))
    
    return prob


def _calculate_yield(
    zone: AgriculturalZone,
    crop: CropType,
    stage: GrowingStage,
    temperature: float,
    humidity: float,
    precipitation: float,
) -> float:
    """Рассчитывает урожайность на основе условий."""
    base_yield = CROP_PARAMS[crop]["base_yield"]
    drought_sens = CROP_PARAMS[crop]["drought_sensitivity"]
    
    # Множитель зоны
    zone_mult = ZONE_PARAMS[zone]["yield_multiplier"]
    
    # Фактор температурного стресса
    optimal_temp = STAGE_OPTIMAL_TEMP[stage]
    temp_diff = abs(temperature - optimal_temp)
    temp_factor = 1.0 - (temp_diff / 30) * drought_sens
    temp_factor = min(1.0, max(0.3, temp_factor))
    
    # Фактор влажности
    humidity_factor = 1.0 - (abs(humidity - 60) / 100) * drought_sens
    humidity_factor = min(1.0, max(0.4, humidity_factor))
    
    # Фактор осадков (положительный до определённого момента)
    precip_factor = min(1.0, precipitation / 60) * 0.3 + 0.7
    
    # Фактор прогресса стадии (поздние стадии = больший потенциал урожая)
    stage_progress = {
        GrowingStage.SOWING: 0.0,
        GrowingStage.EMERGENCE: 0.15,
        GrowingStage.TILLERING: 0.35,
        GrowingStage.BOOTING: 0.55,
        GrowingStage.HEADING_FLOWERING: 0.75,
        GrowingStage.RIPENING_MATURITY: 1.0,
    }
    stage_factor = stage_progress[stage]
    
    # Рассчитываем финальный урожай
    yield_value = (
        base_yield
        * zone_mult
        * temp_factor
        * humidity_factor
        * precip_factor
        * (0.2 + stage_factor * 0.8)
    )
    
    # Добавляем шум
    noise = np.random.normal(0, base_yield * 0.08)
    yield_value = max(1.0, yield_value + noise)
    
    return round(yield_value, 1)


def generate_synthetic_data(
    samples_per_combination: int = 100,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Генерирует синтетические тренировочные данные.
    
    Args:
        samples_per_combination: Количество образцов на каждую комбинацию зона/культура/стадия
        seed: Зерно случайности для воспроизводимости
    
    Returns:
        DataFrame с тренировочными записями
    """
    np.random.seed(seed)
    random.seed(seed)
    
    records: list[TrainingRecord] = []
    
    for zone in AgriculturalZone:
        zone_params = ZONE_PARAMS[zone]
        
        for crop in CropType:
            crop_params = CROP_PARAMS[crop]
            
            for stage in GrowingStage:
                for _ in range(samples_per_combination):
                    # Генерируем погоду с некоторой корреляцией с зоной
                    temp = np.random.normal(
                        zone_params["temp_mean"] + STAGE_OPTIMAL_TEMP[stage] / 3,
                        zone_params["temp_std"],
                    )
                    temp = round(min(40, max(-15, temp)), 1)
                    
                    humidity = np.random.normal(
                        zone_params["humidity_mean"],
                        15,
                    )
                    humidity = min(100, max(20, humidity))
                    
                    precipitation = max(0, np.random.exponential(zone_params["precip_mean"]))
                    precipitation = round(precipitation, 1)
                    
                    # День года на основе стадии
                    stage_days = {
                        GrowingStage.SOWING: (90, 120),
                        GrowingStage.EMERGENCE: (110, 140),
                        GrowingStage.TILLERING: (130, 170),
                        GrowingStage.BOOTING: (160, 200),
                        GrowingStage.HEADING_FLOWERING: (190, 240),
                        GrowingStage.RIPENING_MATURITY: (220, 280),
                    }
                    day_of_year = random.randint(*stage_days[stage])
                    
                    # Рассчитываем целевые переменные
                    disease_prob = _calculate_disease_probability(
                        humidity=humidity,
                        temperature=temp,
                        crop_risk=crop_params["disease_risk"],
                        stage=stage,
                    )
                    
                    yield_value = _calculate_yield(
                        zone=zone,
                        crop=crop,
                        stage=stage,
                        temperature=temp,
                        humidity=humidity,
                        precipitation=precipitation,
                    )
                    
                    record = TrainingRecord(
                        zone=zone,
                        crop_type=crop,
                        growing_stage=stage,
                        stage_day_of_year=day_of_year,
                        temperature=temp,
                        humidity=humidity,
                        precipitation=precipitation,
                        yield_value=yield_value,
                        disease_probability=round(disease_prob, 3),
                    )
                    records.append(record)
    
    df = pd.DataFrame([r.model_dump() for r in records])
    return df


def get_training_data_generator(
    samples_per_combination: int = 100,
    seed: int = 42,
) -> Generator[TrainingRecord, None, None]:
    """Генерирует тренировочные записи по одной."""
    df = generate_synthetic_data(samples_per_combination, seed)
    for _, row in df.iterrows():
        zone_val = str(row["zone"])
        crop_val = str(row["crop_type"])
        stage_val = str(row["growing_stage"])
        yield TrainingRecord(
            zone=AgriculturalZone(zone_val),
            crop_type=CropType(crop_val),
            growing_stage=GrowingStage(stage_val),
            stage_day_of_year=int(row["stage_day_of_year"].item()),
            temperature=float(row["temperature"].item()),
            humidity=float(row["humidity"].item()),
            precipitation=float(row["precipitation"].item()),
            yield_value=float(row["yield_value"].item()),
            disease_probability=float(row["disease_probability"].item()),
        )