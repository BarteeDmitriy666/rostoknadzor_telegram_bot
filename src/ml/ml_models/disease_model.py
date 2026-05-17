"""Модель предсказания заболеваний с использованием Gradient Boosting."""
import joblib
from pathlib import Path

import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report

from src.ml.dataset.schemas import RiskLevel
from src.ml.features.pipeline import FeaturePipeline


# Пороги уровня риска для вероятности
RISK_THRESHOLDS = {
    RiskLevel.GREEN: 0.0,   # 0-0.33
    RiskLevel.YELLOW: 0.33,  # 0.33-0.66
    RiskLevel.RED: 0.66,     # 0.66-1.0
}


def probability_to_risk(probability: float) -> RiskLevel:
    """Конвертирует вероятность в уровень риска."""
    if probability < RISK_THRESHOLDS[RiskLevel.YELLOW]:
        return RiskLevel.GREEN
    elif probability < RISK_THRESHOLDS[RiskLevel.RED]:
        return RiskLevel.YELLOW
    else:
        return RiskLevel.RED


class DiseaseModel:
    """Gradient Boosting классификатор для предсказания риска заболеваний."""
    
    MODEL_NAME = "disease_model.joblib"
    
    def __init__(self) -> None:
        """Инициализирует модель."""
        self.model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
        )
        self.pipeline: FeaturePipeline | None = None
        self.feature_names: list[str] = []
    
    def train(
        self,
        X: list[dict],
        y: list[float],
        pipeline: FeaturePipeline,
    ) -> dict:
        """
        Обучает модель заболеваний.
        
        Args:
            X: Список словарей признаков
            y: Список вероятностей заболеваний (0-1)
            pipeline: Обученный FeaturePipeline
        
        Returns:
            Словарь метрик обучения
        """
        # Конвертируем в DataFrame
        df = pd.DataFrame(X)
        df_transformed = pipeline.transform(df)
        
        # Получаем матрицу признаков
        X_matrix = df_transformed[pipeline.get_feature_names()].values
        
        # Бинизируем вероятности в уровни риска
        y_classes = [probability_to_risk(p) for p in y]
        y_encoded = [list(RiskLevel).index(r) for r in y_classes]
        
        # Обучаем
        self.model.fit(X_matrix, y_encoded)
        self.pipeline = pipeline
        self.feature_names = pipeline.get_feature_names()
        
        # Рассчитываем метрики обучения
        predictions = self.model.predict(X_matrix)
        metrics = {
            "accuracy": accuracy_score(y_encoded, predictions),
            "report": classification_report(y_encoded, predictions, target_names=[r.value for r in RiskLevel]),
        }
        
        return metrics
    
    def predict_proba(self, X: list[dict]) -> list[float]:
        """
        Предсказывает вероятности заболеваний.
        
        Args:
            X: Список словарей признаков
        
        Returns:
            Список вероятностей заболеваний (0-1)
        """
        if self.pipeline is None:
            raise ValueError("Model must be trained before prediction")
        
        df = pd.DataFrame(X)
        df_transformed = self.pipeline.transform(df)
        X_matrix = df_transformed[self.feature_names].values
        
        # Получаем вероятность заболевания (класс индекс 2 = RED, что означает высокий риск)
        # Нам нужна вероятность заболевания, которая коррелирует с более высоким риском
        probas = self.model.predict_proba(X_matrix)
        
        # Рассчитываем взвешенную вероятность
        # Более высокие классы риска вносят больший вклад в общую вероятность заболевания
        disease_probs = []
        for prob in probas:
            # Веса: GREEN=0, YELLOW=0.5, RED=1.0
            weighted_prob = prob[0] * 0 + prob[1] * 0.5 + prob[2] * 1.0
            disease_probs.append(weighted_prob)
        
        return disease_probs
    
    def predict_risk(self, X: list[dict]) -> list[RiskLevel]:
        """
        Предсказывает уровни риска заболеваний.
        
        Args:
            X: Список словарей признаков
        
        Returns:
            Список предсказаний RiskLevel
        """
        probs = self.predict_proba(X)
        return [probability_to_risk(p) for p in probs]
    
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
    def load(cls, path: Path | str) -> "DiseaseModel":
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