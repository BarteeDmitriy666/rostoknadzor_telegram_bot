"""Модель предсказания урожайности с использованием RandomForest."""
import joblib
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import numpy as np

from src.ml.features.pipeline import FeaturePipeline


class YieldModel:
    """RandomForest регрессор для предсказания урожайности культур."""
    
    MODEL_NAME = "yield_model.joblib"
    
    def __init__(self) -> None:
        """Инициализирует модель."""
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )
        self.pipeline: FeaturePipeline | None = None
        self.feature_names: list[str] = []
    
    def train(
        self,
        X: list[dict],
        y: list[float],
        pipeline: FeaturePipeline,
    ) -> dict[str, float]:
        """
        Обучает модель урожайности.
        
        Args:
            X: Список словарей признаков
            y: Список значений урожайности
            pipeline: Обученный FeaturePipeline
        
        Returns:
            Словарь метрик обучения
        """
        # Конвертируем в DataFrame
        df = pd.DataFrame(X)
        df_transformed = pipeline.transform(df)
        
        # Получаем матрицу признаков
        X_matrix = df_transformed[pipeline.get_feature_names()].values
        y_array = list(y)
        
        # Обучаем
        self.model.fit(X_matrix, y_array)
        self.pipeline = pipeline
        self.feature_names = pipeline.get_feature_names()
        
        # Рассчитываем метрики обучения
        predictions = self.model.predict(X_matrix)
        mse = mean_squared_error(y_array, predictions)
        metrics = {
            "mae": mean_absolute_error(y_array, predictions),
            "rmse": np.sqrt(mse),
            "r2": r2_score(y_array, predictions),
        }
        
        return metrics
    
    def predict(self, X: list[dict]) -> list[float]:
        """
        Предсказывает урожайность.
        
        Args:
            X: Список словарей признаков
        
        Returns:
            Список предсказанных урожайностей
        """
        if self.pipeline is None:
            raise ValueError("Model must be trained before prediction")
        
        df = pd.DataFrame(X)
        df_transformed = self.pipeline.transform(df)
        X_matrix = df_transformed[self.feature_names].values
        
        predictions = self.model.predict(X_matrix)
        preds_list = predictions.tolist() if hasattr(predictions, 'tolist') else list(predictions)
        return [float(p) for p in preds_list]
    
    def save(self, path: Path | str) -> None:
        """Сохраняет модель на диск."""
        joblib.dump(
            {
                "model": self.model,
                "pipeline": self.pipeline,
                "feature_names": self.feature_names,
            },
            path,
        )
    
    @classmethod
    def load(cls, path: Path | str) -> "YieldModel":
        """Загружает модель с диска."""
        data = joblib.load(path)
        instance = cls()
        instance.model = data["model"]
        instance.pipeline = data["pipeline"]
        instance.feature_names = data["feature_names"]
        return instance
    
    def get_feature_importance(self) -> dict[str, float]:
        """Возвращает оценки важности признаков."""
        if not hasattr(self.model, "feature_importances_"):
            return {}
        
        return dict(zip(self.feature_names, self.model.feature_importances_))