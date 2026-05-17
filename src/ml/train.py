"""Скрипт для обучения ML моделей."""
import argparse
import joblib
from pathlib import Path

import pandas as pd
from loguru import logger

from src.ml.dataset.generator import generate_synthetic_data
from src.ml.dataset.real_data_loader import load_real_data
from src.ml.dataset.schemas import TrainingRecord
from src.ml.dataset.statistical_augmenter import augment_from_real_data
from src.ml.features.pipeline import create_feature_pipeline
from src.ml.ml_models.disease_model import DiseaseModel
from src.ml.ml_models.yield_model import YieldModel


def train_models(
    samples_per_combination: int = 100,
    output_dir: Path | str = "models",
    real_data_path: Path | str | None = None,
    augment_factor: int = 5,
    seed: int = 42,
) -> dict:
    """
    Обучает модели предсказания урожайности и заболеваний.

    Args:
        samples_per_combination: Количество образцов на каждую комбинацию
            зона/культура/стадия (используется только без реальных данных).
        output_dir: Директория для сохранения обученных моделей.
        real_data_path: Путь к файлу с реальными данными (опционально).
        augment_factor: Сколько синтетических образцов генерировать
            на каждую группу реальных данных.
        seed: Зерно случайности для воспроизводимости.

    Returns:
        Словарь с результатами обучения.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if real_data_path is not None:
        real_df = load_real_data(real_data_path)
        synthetic_df = augment_from_real_data(
            real_df, augment_factor=augment_factor, seed=seed
        )
        df = pd.concat([real_df, synthetic_df], ignore_index=True)
        logger.info(
            f"Combined dataset: {len(df)} samples "
            f"({len(real_df)} real + {len(synthetic_df)} synthetic)"
        )
    else:
        logger.info("Generating synthetic training data...")
        df = generate_synthetic_data(
            samples_per_combination=samples_per_combination,
            seed=seed,
        )
        logger.info(f"Generated {len(df)} training samples")
    
    # Подготавливаем данные
    records = []
    for _, row in df.iterrows():
        records.append(TrainingRecord(**row))
    
    # Разделяем на признаки и целевые переменные
    X_data = [
        {
            "zone": r.zone.value,
            "crop_type": r.crop_type.value,
            "growing_stage": r.growing_stage.value,
            "stage_day_of_year": r.stage_day_of_year,
            "temperature": r.temperature,
            "humidity": r.humidity,
            "precipitation": r.precipitation,
        }
        for r in records
    ]
    y_yield = [r.yield_value for r in records]
    y_disease = [r.disease_probability for r in records]
    
    # Создаём пайплайн признаков
    logger.info("Creating feature pipeline...")
    pipeline, feature_names = create_feature_pipeline(df)
    logger.info(f"Features: {feature_names}")
    
    # Обучаем модель урожайности
    logger.info("Training yield model...")
    yield_model = YieldModel()
    yield_metrics = yield_model.train(X_data, y_yield, pipeline)
    yield_model.save(output_dir / YieldModel.MODEL_NAME)
    logger.info(f"Yield model metrics: {yield_metrics}")
    
    # Обучаем модель заболеваний
    logger.info("Training disease model...")
    disease_model = DiseaseModel()
    disease_metrics = disease_model.train(X_data, y_disease, pipeline)
    disease_model.save(output_dir / DiseaseModel.MODEL_NAME)
    logger.info(f"Disease model accuracy: {disease_metrics['accuracy']:.3f}")
    
    # Сохраняем пайплайн отдельно для инференса
    joblib.dump({"pipeline": pipeline, "feature_names": feature_names}, output_dir / "pipeline.joblib")
    
    # Важность признаков
    logger.info("Feature importance (Yield):")
    for name, importance in sorted(
        yield_model.get_feature_importance().items(),
        key=lambda x: x[1],
        reverse=True,
    ):
        logger.info(f"  {name}: {importance:.4f}")
    
    logger.info("Feature importance (Disease):")
    for name, importance in sorted(
        disease_model.get_feature_importance().items(),
        key=lambda x: x[1],
        reverse=True,
    ):
        logger.info(f"  {name}: {importance:.4f}")
    
    return {
        "yield_metrics": yield_metrics,
        "disease_metrics": disease_metrics,
        "samples": len(df),
        "models_saved": str(output_dir),
    }


def main() -> None:
    """Точка входа в скрипт."""
    parser = argparse.ArgumentParser(description="Train ML models")
    parser.add_argument(
        "-s", "--samples",
        type=int,
        default=100,
        help="Samples per zone/crop/stage combination",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="models",
        help="Output directory for models",
    )
    parser.add_argument(
        "-r", "--real-data",
        type=str,
        default=None,
        help="Path to real training data file (.csv or .parquet)",
    )
    parser.add_argument(
        "-a", "--augment-factor",
        type=int,
        default=5,
        help="Synthetic samples per real group when using real data",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )

    args = parser.parse_args()

    results = train_models(
        samples_per_combination=args.samples,
        output_dir=args.output,
        real_data_path=args.real_data,
        augment_factor=args.augment_factor,
        seed=args.seed,
    )
    
    logger.info("Training complete!")
    logger.info(f"Results: {results}")


if __name__ == "__main__":
    main()