"""Тесты для ML модуля."""
from datetime import datetime

import pytest

from loguru import logger

from src.ml.dataset.schemas import (
    AgriculturalZone,
    CropType,
    GrowingStage,
    ModelInput,
    WeatherInput,
)
from src.ml.predict import get_predictor


@pytest.fixture(scope="module")
def predictor():
    """Загружаем предиктор один раз для всех тестов."""
    return get_predictor()


def test_predict_yield(predictor):
    """Тест предсказания урожайности."""
    model_input = ModelInput(
        zone=AgriculturalZone.CENTRAL_IRRIGATED,
        crop_type=CropType.CORN,
        growing_stage=GrowingStage.BOOTING,
        stage_timestamp=datetime(2024, 6, 15),
        weather=WeatherInput(temperature=25, humidity=65, precipitation=15),
    )
    
    logger.info(f"test_predict_yield | input: zone={model_input.zone}, crop={model_input.crop_type}, "
                f"stage={model_input.growing_stage}, weather={model_input.weather.model_dump()}")
    
    result = predictor.predict(model_input)
    
    # Получаем заболевание из временной шкалы
    disease = result.disease_timeline[0]
    
    logger.info(f"test_predict_yield | output: yield_forecast={result.yield_forecast:.4f}, "
                f"disease_prob={disease.probability:.4f}, "
                f"risk_level={disease.risk_level.value}")
    
    assert isinstance(result.yield_forecast, float)
    assert result.yield_forecast > 0
    assert disease.probability >= 0
    assert disease.probability <= 1


def test_disease_risk_levels(predictor):
    """Тест преобразования уровня риска заболевания."""
    model_input = ModelInput(
        zone=AgriculturalZone.SOUTH,
        crop_type=CropType.SUNFLOWER,
        growing_stage=GrowingStage.HEADING_FLOWERING,
        stage_timestamp=datetime(2024, 7, 1),
        weather=WeatherInput(temperature=30, humidity=85, precipitation=5),
    )
    
    logger.info(f"test_disease_risk_levels | input: zone={model_input.zone}, crop={model_input.crop_type}, "
                f"stage={model_input.growing_stage}, weather={model_input.weather.model_dump()}")
    
    result = predictor.predict(model_input)
    
    # Получаем заболевание из временной шкалы
    disease = result.disease_timeline[0]
    
    logger.info(f"test_disease_risk_levels | output: yield_forecast={result.yield_forecast:.4f}, "
                f"disease_prob={disease.probability:.4f}, "
                f"risk_level={disease.risk_level.value}")
    
    assert disease.risk_level.value in ["green", "yellow", "red"]


def test_all_zones(predictor):
    """Тест предсказания для всех зон."""
    for zone in AgriculturalZone:
        model_input = ModelInput(
            zone=zone,
            crop_type=CropType.WINTER_WHEAT,
            growing_stage=GrowingStage.TILLERING,
            stage_timestamp=datetime(2024, 4, 15),
            weather=WeatherInput(temperature=15, humidity=60, precipitation=10),
        )
        
        logger.info(f"test_all_zones | input: zone={zone.value}, crop={model_input.crop_type}, "
                    f"stage={model_input.growing_stage}, weather={model_input.weather.model_dump()}")
        
        result = predictor.predict(model_input)
        
        logger.info(f"test_all_zones | output: zone={zone.value}, yield_forecast={result.yield_forecast:.4f}")
        
        assert result.yield_forecast > 0


def test_all_crops(predictor):
    """Тест предсказания для всех культур."""
    for crop in CropType:
        model_input = ModelInput(
            zone=AgriculturalZone.AZOV,
            crop_type=crop,
            growing_stage=GrowingStage.EMERGENCE,
            stage_timestamp=datetime(2024, 5, 1),
            weather=WeatherInput(temperature=18, humidity=55, precipitation=8),
        )
        
        logger.info(f"test_all_crops | input: zone={model_input.zone}, crop={crop.value}, "
                    f"stage={model_input.growing_stage}, weather={model_input.weather.model_dump()}")
        
        result = predictor.predict(model_input)
        
        logger.info(f"test_all_crops | output: crop={crop.value}, yield_forecast={result.yield_forecast:.4f}")
        
        assert result.yield_forecast > 0
