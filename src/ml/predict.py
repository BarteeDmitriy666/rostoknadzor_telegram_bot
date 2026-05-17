"""Унифицированный интерфейс предсказания для ML моделей."""
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger

from src.ml.dataset.schemas import (
    DiseaseForecast,
    ModelInput,
    ModelOutput,
    RiskLevel,
)
from src.ml.ml_models.disease_model import DiseaseModel
from src.ml.ml_models.yield_model import YieldModel


class CropPredictor:
    """Унифицированный интерфейс для предсказания урожайности и заболеваний."""
    
    def __init__(self, models_dir: Path | str = "models") -> None:
        """
        Инициализирует предиктор.
        
        Args:
            models_dir: Директория с обученными моделями
        """
        self.models_dir = Path(models_dir)
        self._yield_model: YieldModel | None = None
        self._disease_model: DiseaseModel | None = None
        self._loaded = False
    
    def load_models(self) -> None:
        """Загружает обученные модели с диска."""
        yield_path = self.models_dir / YieldModel.MODEL_NAME
        disease_path = self.models_dir / DiseaseModel.MODEL_NAME
        
        if not yield_path.exists():
            raise FileNotFoundError(f"Yield model not found: {yield_path}")
        if not disease_path.exists():
            raise FileNotFoundError(f"Disease model not found: {disease_path}")
        
        logger.info(f"Loading models from {self.models_dir}")
        self._yield_model = YieldModel.load(yield_path)
        self._disease_model = DiseaseModel.load(disease_path)
        self._loaded = True
        logger.info("Models loaded successfully")
    
    def predict(self, model_input: ModelInput) -> ModelOutput:
        """
        Выполняет комбинированное предсказание урожайности и риска заболеваний.
        
        Args:
            model_input: Входные данные для предсказания
        
        Returns:
            Комбинированный прогноз урожайности и заболеваний
        """
        if not self._loaded:
            self.load_models()
        
        # Подготавливаем признаки для модели
        features = self._prepare_features(model_input)
        
        # Предсказываем урожайность
        # Модель обучена на исторических данных по урожайности культур
        yield_pred = self._yield_model.predict([features])[0]
        yield_forecast = round(float(yield_pred), 1)
        
        # Предсказываем риск заболеваний
        # Gradient Boosting хорошо справляется с классификацией рисков
        disease_prob = self._disease_model.predict_proba([features])[0]
        disease_forecast = DiseaseForecast(
            probability=round(float(disease_prob), 3),
            risk_level=RiskLevel.from_probability(disease_prob),
            date=model_input.stage_timestamp,
        )
        
        # Рассчитываем примерную дату уборки (грубая оценка)
        # Обычно от посева до уборки проходит около 90 дней
        harvest_date = model_input.stage_timestamp + timedelta(days=90)
        
        return ModelOutput(
            yield_forecast=yield_forecast,
            yield_date=harvest_date,
            disease_timeline=[disease_forecast],
            prediction_timestamp=datetime.now(),
        )
    
    def _prepare_features(self, model_input: ModelInput) -> dict:
        """Подготавливает признаки из входных данных модели."""
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
    
    def predict_yield_only(self, model_input: ModelInput) -> float:
        """Предсказывает только урожайность."""
        if not self._loaded:
            self.load_models()
        
        features = self._prepare_features(model_input)
        yield_pred = self._yield_model.predict([features])[0]
        return round(float(yield_pred), 1)
    
    def predict_disease_only(self, model_input: ModelInput) -> DiseaseForecast:
        """Предсказывает только риск заболеваний."""
        if not self._loaded:
            self.load_models()
        
        features = self._prepare_features(model_input)
        disease_prob = self._disease_model.predict_proba([features])[0]
        
        return DiseaseForecast(
            probability=round(float(disease_prob), 3),
            risk_level=RiskLevel.from_probability(disease_prob),
            date=model_input.stage_timestamp,
        )


# Глобальный экземпляр предиктора для интеграции с ботом
_predictor: CropPredictor | None = None


def get_predictor(models_dir: Path | str = "models") -> CropPredictor:
    """Получает или создаёт глобальный экземпляр предиктора."""
    global _predictor
    if _predictor is None:
        _predictor = CropPredictor(models_dir)
        _predictor.load_models()
    return _predictor


def predict(model_input: ModelInput) -> ModelOutput:
    """
    Удобная функция для выполнения предсказания.
    
    Args:
        model_input: Входные данные
    
    Returns:
        Комбинированный прогноз
    """
    return get_predictor().predict(model_input)