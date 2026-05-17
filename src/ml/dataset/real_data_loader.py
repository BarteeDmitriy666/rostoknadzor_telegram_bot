"""Загрузчик и валидатор реальных тренировочных данных."""
from pathlib import Path

import pandas as pd
from loguru import logger

from src.ml.dataset.schemas import AgriculturalZone, CropType, GrowingStage

REQUIRED_COLUMNS = [
    "zone",
    "crop_type",
    "growing_stage",
    "stage_day_of_year",
    "temperature",
    "humidity",
    "precipitation",
    "yield_value",
    "disease_probability",
]

VALID_ZONES = {z.value for z in AgriculturalZone}
VALID_CROPS = {c.value for c in CropType}
VALID_STAGES = {s.value for s in GrowingStage}

NUMERIC_COLUMNS = [
    "stage_day_of_year",
    "temperature",
    "humidity",
    "precipitation",
    "yield_value",
    "disease_probability",
]


def load_real_data(path: Path | str) -> pd.DataFrame:
    """
    Загружает реальные данные из CSV или Parquet, валидирует схему и значения.

    Args:
        path: Путь к файлу данных (.csv или .parquet).

    Returns:
        DataFrame с валидированными реальными записями.

    Raises:
        FileNotFoundError: Если файл не существует.
        ValueError: Если схема некорректна или есть недопустимые значения.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Real data file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(path)
    elif suffix in (".parquet", ".pq"):
        df = pd.read_parquet(path)
    else:
        raise ValueError(
            f"Unsupported file format: {suffix}. Use .csv or .parquet"
        )

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df[REQUIRED_COLUMNS].copy()

    invalid_zones = set(df["zone"].unique()) - VALID_ZONES
    if invalid_zones:
        raise ValueError(
            f"Invalid zone values: {invalid_zones}. Valid: {VALID_ZONES}"
        )

    invalid_crops = set(df["crop_type"].unique()) - VALID_CROPS
    if invalid_crops:
        raise ValueError(
            f"Invalid crop_type values: {invalid_crops}. Valid: {VALID_CROPS}"
        )

    invalid_stages = set(df["growing_stage"].unique()) - VALID_STAGES
    if invalid_stages:
        raise ValueError(
            f"Invalid growing_stage values: {invalid_stages}. "
            f"Valid: {VALID_STAGES}"
        )

    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if df[NUMERIC_COLUMNS].isnull().any().any():
        bad_rows = df[NUMERIC_COLUMNS].isnull().any(axis=1).sum()
        raise ValueError(
            f"Found {bad_rows} rows with non-numeric or missing "
            f"values in numeric columns"
        )

    if (df["disease_probability"] < 0).any() or (
        df["disease_probability"] > 1
    ).any():
        raise ValueError("disease_probability must be in [0, 1]")

    if (df["stage_day_of_year"] < 1).any() or (
        df["stage_day_of_year"] > 366
    ).any():
        raise ValueError("stage_day_of_year must be in [1, 366]")

    if (df["humidity"] < 0).any() or (df["humidity"] > 100).any():
        raise ValueError("humidity must be in [0, 100]")

    if (df["precipitation"] < 0).any():
        raise ValueError("precipitation must be >= 0")

    df["zone"] = df["zone"].astype(str)
    df["crop_type"] = df["crop_type"].astype(str)
    df["growing_stage"] = df["growing_stage"].astype(str)

    logger.info(f"Loaded {len(df)} real training records from {path}")
    return df
