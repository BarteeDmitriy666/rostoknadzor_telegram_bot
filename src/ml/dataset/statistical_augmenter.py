"""Генерация синтетических данных на основе статистических распределений
реальных данных."""

import numpy as np
import pandas as pd
from loguru import logger

from src.ml.dataset.generator import (
    CROP_PARAMS,
    STAGE_OPTIMAL_TEMP,
    ZONE_PARAMS,
    _calculate_disease_probability,
    _calculate_yield,
)
from src.ml.dataset.schemas import AgriculturalZone, CropType, GrowingStage

NUMERIC_FEATURES = [
    "temperature",
    "humidity",
    "precipitation",
    "stage_day_of_year",
]
MIN_SAMPLES_FOR_STATS = 3

_STAGE_DAY_RANGES = {
    GrowingStage.SOWING: (90, 120),
    GrowingStage.EMERGENCE: (110, 140),
    GrowingStage.TILLERING: (130, 170),
    GrowingStage.BOOTING: (160, 200),
    GrowingStage.HEADING_FLOWERING: (190, 240),
    GrowingStage.RIPENING_MATURITY: (220, 280),
}


def _fallback_record(
    zone: AgriculturalZone,
    crop: CropType,
    stage: GrowingStage,
) -> dict:
    """Генерирует одну синтетическую запись через исходные зональные параметры."""
    zone_params = ZONE_PARAMS[zone]
    crop_params = CROP_PARAMS[crop]

    temp = np.random.normal(
        zone_params["temp_mean"] + STAGE_OPTIMAL_TEMP[stage] / 3,
        zone_params["temp_std"],
    )
    temp = round(min(40.0, max(-15.0, temp)), 1)

    humidity = np.random.normal(zone_params["humidity_mean"], 15)
    humidity = min(100.0, max(20.0, humidity))

    precipitation = max(0.0, np.random.exponential(zone_params["precip_mean"]))
    precipitation = round(precipitation, 1)

    day_of_year = int(np.random.randint(*_STAGE_DAY_RANGES[stage]))

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

    return {
        "zone": zone.value,
        "crop_type": crop.value,
        "growing_stage": stage.value,
        "stage_day_of_year": day_of_year,
        "temperature": temp,
        "humidity": round(humidity, 1),
        "precipitation": precipitation,
        "yield_value": yield_value,
        "disease_probability": round(disease_prob, 3),
    }


def augment_from_real_data(
    real_df: pd.DataFrame,
    augment_factor: int = 5,
    seed: int | None = None,
) -> pd.DataFrame:
    """
    Генерирует синтетические данные, обучаясь на статистиках реальных данных.

    Для каждой комбинации (zone, crop_type, growing_stage):
    - Если реальных записей >= MIN_SAMPLES_FOR_STATS, семплируем новые строки
      из многомерного нормального распределения, построенного по реальным
      temperature, humidity, precipitation, stage_day_of_year.
    - Если записей меньше, используем fallback на исходные зональные параметры.
    Целевые переменные вычисляются детерминированно с помощью тех же формул,
    что и в generator.py.

    Args:
        real_df: DataFrame с реальными записями.
        augment_factor: Сколько синтетических образцов генерировать
            на каждую группу.
        seed: Зерно случайности.

    Returns:
        DataFrame с синтетическими записями.
    """
    if seed is not None:
        np.random.seed(seed)

    synthetic_records: list[dict] = []

    grouped = real_df.groupby(
        ["zone", "crop_type", "growing_stage"], sort=False
    )

    for (zone_str, crop_str, stage_str), group in grouped:
        zone = AgriculturalZone(zone_str)
        crop = CropType(crop_str)
        stage = GrowingStage(stage_str)

        n_real = len(group)

        if n_real >= MIN_SAMPLES_FOR_STATS:
            numeric_df = group[NUMERIC_FEATURES].astype(float)
            mean = numeric_df.mean().values
            cov = numeric_df.cov().values
            cov = cov + np.eye(len(NUMERIC_FEATURES)) * 1e-6

            samples = np.random.multivariate_normal(
                mean, cov, size=augment_factor
            )

            for sample in samples:
                temp, humidity, precipitation, day_of_year = sample

                temp = round(min(40.0, max(-15.0, temp)), 1)
                humidity = min(100.0, max(20.0, humidity))
                precipitation = max(0.0, round(precipitation, 1))
                day_of_year = int(min(366, max(1, round(day_of_year))))

                disease_prob = _calculate_disease_probability(
                    humidity=humidity,
                    temperature=temp,
                    crop_risk=CROP_PARAMS[crop]["disease_risk"],
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

                synthetic_records.append(
                    {
                        "zone": zone_str,
                        "crop_type": crop_str,
                        "growing_stage": stage_str,
                        "stage_day_of_year": day_of_year,
                        "temperature": temp,
                        "humidity": round(humidity, 1),
                        "precipitation": precipitation,
                        "yield_value": yield_value,
                        "disease_probability": round(disease_prob, 3),
                    }
                )
        else:
            logger.debug(
                f"Group ({zone_str}, {crop_str}, {stage_str}) has only "
                f"{n_real} real samples; using fallback generator."
            )
            for _ in range(augment_factor):
                synthetic_records.append(
                    _fallback_record(zone, crop, stage)
                )

    df = pd.DataFrame(synthetic_records)
    logger.info(
        f"Generated {len(df)} augmented samples from {len(real_df)} "
        f"real records"
    )
    return df
