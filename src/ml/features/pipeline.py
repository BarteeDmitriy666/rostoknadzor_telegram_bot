"""Пайплайн создания признаков для ML моделей."""
from typing import Any

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler

from src.ml.dataset.schemas import ModelInput


class FeaturePipeline:
    """Пайплайн создания признаков для сельскохозяйственных ML предсказаний."""
    
    def __init__(self) -> None:
        """Инициализирует кодировщики и скейлеры."""
        self.zone_encoder = LabelEncoder()
        self.crop_encoder = LabelEncoder()
        self.stage_encoder = LabelEncoder()
        
        self.weather_scaler = StandardScaler()
        self.temporal_scaler = StandardScaler()
        
        self._fitted = False
    
    def fit(self, df: pd.DataFrame) -> "FeaturePipeline":
        """
        Обучает пайплайн на тренировочных данных.
        
        Args:
            df: Тренировочный DataFrame с zone, crop_type, growing_stage и т.д.
        """
        # Обучаем кодировщики категориальных признаков
        self.zone_encoder.fit(df["zone"])
        self.crop_encoder.fit(df["crop_type"])
        self.stage_encoder.fit(df["growing_stage"])
        
        # Обучаем скейлеры
        weather_cols = ["temperature", "humidity", "precipitation"]
        self.weather_scaler.fit(df[weather_cols])
        
        temporal_cols = ["stage_day_of_year"]
        self.temporal_scaler.fit(df[temporal_cols])
        
        self._fitted = True
        return self
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Трансформирует данные с помощью обученных кодировщиков и скейлеров.
        
        Args:
            df: Входной DataFrame
        
        Returns:
            Трансформированный DataFrame с числовыми признаками
        """
        if not self._fitted:
            raise ValueError("Pipeline must be fitted before transform")
        
        result = df.copy()
        
        # Кодируем категориальные признаки
        result["zone_encoded"] = self.zone_encoder.transform(result["zone"])
        result["crop_encoded"] = self.crop_encoder.transform(result["crop_type"])
        result["stage_encoded"] = self.stage_encoder.transform(result["growing_stage"])
        
        # Масштабируем погодные признаки
        weather_cols = ["temperature", "humidity", "precipitation"]
        result[weather_cols] = self.weather_scaler.transform(result[weather_cols])
        
        # Масштабируем временные признаки
        result["day_of_year_scaled"] = self.temporal_scaler.transform(
            result[["stage_day_of_year"]]
        )
        
        # Создаём циклические признаки для дня года
        result["day_sin"] = np.sin(2 * np.pi * result["stage_day_of_year"] / 365)
        result["day_cos"] = np.cos(2 * np.pi * result["stage_day_of_year"] / 365)
        
        # Признаки взаимодействия погоды
        result["temp_humidity_interaction"] = (
            result["temperature"] * result["humidity"] / 100
        )
        result["heat_stress"] = np.maximum(0, result["temperature"] - 25)
        result["cold_stress"] = np.maximum(0, 10 - result["temperature"])
        
        # Индикатор риска высокой влажности
        result["high_humidity_risk"] = (result["humidity"] > 70).astype(float)
        
        return result
    
    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Обучает и трансформирует за один шаг."""
        return self.fit(df).transform(df)
    
    def get_feature_names(self) -> list[str]:
        """Возвращает список имён признаков после трансформации."""
        return [
            "zone_encoded",
            "crop_encoded", 
            "stage_encoded",
            "temperature",
            "humidity",
            "precipitation",
            "day_of_year_scaled",
            "day_sin",
            "day_cos",
            "temp_humidity_interaction",
            "heat_stress",
            "cold_stress",
            "high_humidity_risk",
        ]
    
    def input_to_features(self, model_input: ModelInput) -> dict[str, Any]:
        """
        Конвертирует ModelInput в словарь признаков для предсказания.
        
        Args:
            model_input: Входные данные от бота/пользователя
        
        Returns:
            Словарь признаков, готовый для предсказания модели
        """
        day_of_year = model_input.stage_timestamp.timetuple().tm_yday
        
        return {
            "zone": model_input.zone.value,
            "crop_type": model_input.crop_type.value,
            "growing_stage": model_input.growing_stage.value,
            "stage_day_of_year": day_of_year,
            "temperature": model_input.weather.temperature,
            "humidity": model_input.weather.humidity,
            "precipitation": model_input.weather.precipitation,
        }
    
    def input_to_dataframe(self, model_input: ModelInput) -> pd.DataFrame:
        """
        Конвертирует ModelInput в DataFrame для предсказания.
        
        Args:
            model_input: Входные данные от бота/пользователя
        
        Returns:
            DataFrame, готовый для transform()
        """
        features = self.input_to_features(model_input)
        return pd.DataFrame([features])


def create_feature_pipeline(df: pd.DataFrame) -> tuple[FeaturePipeline, list[str]]:
    """
    Создаёт и обучает пайплайн признаков.
    
    Args:
        df: Тренировочный DataFrame
    
    Returns:
        Кортеж из (обученный пайплайн, имена признаков)
    """
    pipeline = FeaturePipeline()
    pipeline.fit(df)
    return pipeline, pipeline.get_feature_names()