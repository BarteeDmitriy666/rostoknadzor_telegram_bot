"""Схемы данных для ML моделей."""
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class AgriculturalZone(str, Enum):
    """Сельскохозяйственные зоны Ростовской области."""
    NORTHWEST = "northwest"
    NORTHEAST = "northeast"
    CENTRAL_IRRIGATED = "central_irrigated"
    AZOV = "azov"
    SOUTH = "south"
    EAST = "east"


class CropType(str, Enum):
    """Доступные типы культур."""
    # Зерновые и бобовые
    WINTER_WHEAT = "winter_wheat"
    SPRING_BARLEY = "spring_barley"
    CORN = "corn"
    OATS = "oats"
    RYE = "rye"
    MILLET = "millet"
    SORGHUM = "sorghum"
    PEAS = "peas"
    CHICKPEAS = "chickpeas"
    # Промышленные и масличные культуры
    SUNFLOWER = "sunflower"
    SUGAR_BEET = "sugar_beet"
    SOYBEANS = "soybeans"
    FLAX = "flax"
    MUSTARD = "mustard"
    # Овощи и фрукты
    POTATOES = "potatoes"
    TOMATOES = "tomatoes"
    ONIONS = "onions"
    APPLES = "apples"
    PLUMS = "plums"
    GRAPES = "grapes"


class GrowingStage(str, Enum):
    """Стадии роста культур."""
    SOWING = "sowing"
    EMERGENCE = "emergence"
    TILLERING = "tillering"
    BOOTING = "booting"
    HEADING_FLOWERING = "heading_flowering"
    RIPENING_MATURITY = "ripening_maturity"


class RiskLevel(str, Enum):
    """Интерпретация уровня риска заболеваний."""
    GREEN = "green"    # Низкий риск (0-0.33)
    YELLOW = "yellow"  # Средний риск (0.33-0.66)
    RED = "red"        # Высокий риск (0.66-1.0)
    
    @classmethod
    def from_probability(cls, probability: float) -> "RiskLevel":
        """Конвертирует вероятность в уровень риска."""
        if probability < 0.33:
            return cls.GREEN
        elif probability < 0.66:
            return cls.YELLOW
        return cls.RED


class WeatherInput(BaseModel):
    """Входные данные о погоде."""
    temperature: float = Field(description="Температура в градусах Цельсия")
    humidity: float = Field(description="Влажность в процентах (0-100)")
    precipitation: float = Field(description="Осадки в мм")


class ModelInput(BaseModel):
    """Входные данные для ML предсказания."""
    zone: AgriculturalZone
    crop_type: CropType
    growing_stage: GrowingStage
    stage_timestamp: datetime
    weather: WeatherInput


class DiseaseForecast(BaseModel):
    """Результат прогноза заболеваний."""
    probability: float = Field(description="Вероятность заболевания (0-1)")
    risk_level: RiskLevel = Field(description="Уровень риска (светофор)")
    date: datetime = Field(description="Дата прогноза")


class ModelOutput(BaseModel):
    """Комбинированный результат модели."""
    yield_forecast: float = Field(description="Урожайность в ц/га")
    yield_date: datetime = Field(description="Ожидаемая дата уборки")
    disease_timeline: list[DiseaseForecast] = Field(description="Временная шкала риска заболеваний")
    model_version: str = Field(default="1.0.0")
    prediction_timestamp: datetime = Field(default_factory=datetime.now)


class StageInfo(BaseModel):
    """Информация о стадии роста."""
    stage: GrowingStage
    start_date: datetime
    end_date: datetime
    weather: WeatherInput
    disease_forecast: DiseaseForecast
    yield_contribution: float = Field(default=0.0, description="Урожай на этой стадии (частичный)")


class SeasonForecast(BaseModel):
    """Полный прогноз сезона от посева до уборки."""
    zone: AgriculturalZone
    crop_type: CropType
    sowing_date: datetime
    harvest_date: datetime
    yield_forecast: float
    stages: list[StageInfo]
    monthly_risk: dict[str, RiskLevel] = Field(default_factory=dict)
    model_version: str = Field(default="1.0.0")
    prediction_timestamp: datetime = Field(default_factory=datetime.now)


class TrainingRecord(BaseModel):
    """Запись тренировочных данных."""
    zone: AgriculturalZone
    crop_type: CropType
    growing_stage: GrowingStage
    stage_day_of_year: int
    temperature: float
    humidity: float
    precipitation: float
    # Целевые переменные
    yield_value: float = Field(description="Урожай в ц/га")
    disease_probability: float = Field(description="Вероятность заболевания (0-1)")