"""Генератор прогноза сезона - полная временная шкала от посева до уборки."""
import threading
from datetime import datetime
from typing import Optional

from loguru import logger

from src.ml.dataset.schemas import (
    AgriculturalZone,
    CropType,
    DiseaseForecast,
    GrowingStage,
    ModelInput,
    RiskLevel,
    SeasonForecast,
    StageInfo
)
from src.ml.dataset.stage_calendar import calculate_season_timeline, get_harvest_date
from src.ml.dataset.weather_generator import generate_weather
from src.ml.ml_models.disease_model import DiseaseModel
from src.ml.ml_models.yield_model import YieldModel


# Магические числа в виде констант
# YIELD_STAGE_MULTIPLIER - вклад финальной стадии в урожай (30%)
# DURATION_NORMALIZATION - дни для нормализации урожайности
YIELD_STAGE_MULTIPLIER = 0.3  # Вклад финальной стадии в урожайность
DURATION_NORMALIZATION = 200   # Дни для нормализации урожайности

# Блокировка для паттерна одиночки (singleton)
# Паттерн одиночки гарантирует одну копию forecaster во всей системе
_forecaster_lock = threading.Lock()


class SeasonForecaster:
    """Генерирует полный прогноз сезона от посева до уборки."""
    
    def __init__(self, models_dir: str = "models") -> None:
        """
        Инициализирует генератор прогнозов.
        
        Args:
            models_dir: Директория с обученными моделями
        """
        self.models_dir = models_dir
        self._yield_model: Optional[YieldModel] = None
        self._disease_model: Optional[DiseaseModel] = None
        self._loaded = False
    
    def load_models(self) -> None:
        """Загружает обученные модели из директории."""
        if self._loaded:
            return
        
        logger.info(f"Loading models from {self.models_dir}")
        self._yield_model = YieldModel.load(f"{self.models_dir}/yield_model.joblib")
        self._disease_model = DiseaseModel.load(f"{self.models_dir}/disease_model.joblib")
        self._loaded = True
        logger.info("Models loaded successfully")
    
    def forecast(
        self,
        zone: AgriculturalZone,
        crop: CropType,
        sowing_date: datetime,
    ) -> SeasonForecast:
        """
        Генерирует полный прогноз сезона от посева до уборки.
        
        Args:
            zone: Сельскохозяйственная зона
            crop: Тип культуры
            sowing_date: Дата посева
        
        Returns:
            SeasonForecast с полной временной шкалой
        """
        self.load_models()
        
        harvest_date = get_harvest_date(sowing_date, crop)
        timeline = calculate_season_timeline(sowing_date, crop, zone)
        
        # Рассчитываем среднюю погоду для прогноза урожайности
        # Средняя погода за сезон даёт более стабильный прогноз
        mid_season = sowing_date + (harvest_date - sowing_date) // 2
        avg_weather = generate_weather(zone, mid_season)
        
        # Предсказываем финальную урожайность
        # Используем стадию созревания как целевую точку прогноза
        yield_input = ModelInput(
            zone=zone,
            crop_type=crop,
            growing_stage=GrowingStage.RIPENING_MATURITY,
            stage_timestamp=harvest_date,
            weather=avg_weather,
        )
        
        features = self._prepare_features(yield_input)
        yield_forecast = self._yield_model.predict([features])[0]
        yield_forecast = round(float(yield_forecast), 1)
        
        # Генерируем прогноз по стадиям
        # Для каждой стадии рассчитываем погоду и риск заболеваний
        stages: list[StageInfo] = []
        
        for stage_data in timeline:
            stage = stage_data["stage"]
            stage_start = stage_data["start_date"]
            stage_end = stage_data["end_date"]
            
            # Генерируем погоду для этой стадии
            # Погода влияет на риск заболеваний и развитие растения
            stage_weather = generate_weather(zone, stage_start)
            
            # Предсказываем риск заболеваний для текущей стадии
            # Риск зависит от стадии развития и погодных условий
            disease_input = ModelInput(
                zone=zone,
                crop_type=crop,
                growing_stage=stage,
                stage_timestamp=stage_start,
                weather=stage_weather,
            )
            disease_features = self._prepare_features(disease_input)
            disease_prob = self._disease_model.predict_proba([disease_features])[0]
            
            disease_forecast = DiseaseForecast(
                probability=round(float(disease_prob), 3),
                risk_level=RiskLevel.from_probability(disease_prob),
                date=stage_start,
            )
            
            # Рассчитываем вклад стадии в общую урожайность
            # Урожай накапливается по мере развития растения
            # На стадии созревания происходит финальный прирост урожая
            stage_yield = yield_forecast * stage_data["duration_days"] / DURATION_NORMALIZATION
            if stage == GrowingStage.RIPENING_MATURITY:
                stage_yield = yield_forecast * YIELD_STAGE_MULTIPLIER  # Финальный всплеск урожайности
            
            stage_info = StageInfo(
                stage=stage,
                start_date=stage_start,
                end_date=stage_end,
                weather=stage_weather,
                disease_forecast=disease_forecast,
                yield_contribution=round(stage_yield, 1),
            )
            stages.append(stage_info)
        
        # Рассчитываем сводку рисков по месяцам
        # Усредняем риск по всем стадиям в каждом месяце
        monthly_risk = self._calculate_monthly_risk(stages)
        
        return SeasonForecast(
            zone=zone,
            crop_type=crop,
            sowing_date=sowing_date,
            harvest_date=harvest_date,
            yield_forecast=yield_forecast,
            stages=stages,
            monthly_risk=monthly_risk,
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
    
    def _calculate_monthly_risk(self, stages: list[StageInfo]) -> dict[str, RiskLevel]:
        """Рассчитывает средний риск по месяцам."""
        monthly_probs: dict[str, list[float]] = {}
        
        for stage in stages:
            month_key = stage.start_date.strftime("%B")  # Полное название месяца
            if month_key not in monthly_probs:
                monthly_probs[month_key] = []
            monthly_probs[month_key].append(stage.disease_forecast.probability)
        
        result = {}
        for month, probs in monthly_probs.items():
            avg_prob = sum(probs) / len(probs)
            result[month] = RiskLevel.from_probability(avg_prob)
        
        return result


# Глобальный экземпляр генератора прогнозов
# Использует паттерн одиночки для экономии ресурсов
_forecaster: SeasonForecaster | None = None


def get_forecaster(models_dir: str = "models") -> SeasonForecaster:
    """Получает или создаёт глобальный экземпляр генератора прогнозов (потокобезопасный).
    
    Паттерн двойной проверки (double-check locking) используется для
    безопасной инициализации в многопоточной среде.
    """
    global _forecaster
    if _forecaster is None:
        with _forecaster_lock:
            # Двойная проверка для потокобезопасности
            if _forecaster is None:
                _forecaster = SeasonForecaster(models_dir)
                _forecaster.load_models()
    return _forecaster


def forecast_season(
    zone: AgriculturalZone,
    crop: CropType,
    sowing_date: datetime,
    models_dir: str = "models",
) -> SeasonForecast:
    """
    Удобная функция для получения прогноза сезона.
    
    Args:
        zone: Сельскохозяйственная зона
        crop: Тип культуры
        sowing_date: Дата посева
        models_dir: Директория с моделями
    
    Returns:
        SeasonForecast с полной временной шкалой
    """
    return get_forecaster(models_dir).forecast(zone, crop, sowing_date)