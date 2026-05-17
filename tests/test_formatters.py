"""Тесты для форматтеров сообщений."""
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.bot.formatters import (
    format_cancel_message,
    format_chart_caption_monthly,
    format_chart_caption_timeline,
    format_chart_generating,
    format_crop_detail,
    format_crop_selection,
    format_crops_list,
    format_forecast_detail,
    format_forecast_list_item,
    format_forecast_result,
    format_forecast_saved,
    format_help_message,
    format_my_forecasts_header,
    format_new_forecast_button,
    format_no_forecasts,
    format_region_detail,
    format_regions_list,
    format_sowing_date_prompt,
    format_start_message,
    format_zone_selection,
)
from src.ml.dataset.schemas import (
    AgriculturalZone,
    CropType,
    GrowingStage,
    RiskLevel,
    SeasonForecast,
)


class TestMainMessages:
    """Тесты для основных командных сообщений."""

    def test_format_start_message(self):
        """Тест формата стартового сообщения."""
        msg = format_start_message()
        
        assert "АгроБот" in msg
        assert "прогноз урожайности" in msg.lower()
        assert "Ростовской области" in msg

    def test_format_help_message(self):
        """Тест формата сообщения помощи."""
        msg = format_help_message()
        
        assert "справка" in msg.lower()
        assert "/predict" in msg
        assert "/myforecasts" in msg
        assert "риск" in msg.lower()

    def test_format_cancel_message(self):
        """Тест формата сообщения отмены."""
        msg = format_cancel_message()
        
        assert "отменено" in msg.lower()

    def test_format_error_message(self):
        """Тест формата сообщения об ошибке."""
        from src.bot.formatters import format_error_message
        
        msg = format_error_message("Test error")
        
        assert "ошибка" in msg.lower()
        assert "Test error" in msg


class TestPredictionFlowMessages:
    """Тесты для сообщений процесса предсказания."""

    def test_format_zone_selection(self):
        """Тест запроса выбора зоны."""
        msg = format_zone_selection()
        
        assert "выберите регион" in msg.lower()
        assert "сельскохозяйственн" in msg.lower()

    def test_format_crop_selection(self):
        """Тест запроса выбора культуры."""
        msg = format_crop_selection(AgriculturalZone.SOUTH)
        
        assert "выберите культуру" in msg.lower()
        assert "Юг" in msg

    def test_format_sowing_date_prompt(self):
        """Тест запроса даты посева."""
        msg = format_sowing_date_prompt(
            AgriculturalZone.SOUTH,
            CropType.WINTER_WHEAT,
        )
        
        assert "дату посева" in msg.lower()
        assert "ДД.ММ.ГГГГ" in msg
        assert "Юг" in msg

    def test_format_forecast_result(self):
        """Тест формата результата прогноза."""
        # Создаём мок прогноза
        forecast = MagicMock(spec=SeasonForecast)
        forecast.zone = AgriculturalZone.SOUTH
        forecast.crop_type = CropType.WINTER_WHEAT
        forecast.sowing_date = datetime(2024, 4, 1)
        forecast.harvest_date = datetime(2024, 7, 15)
        forecast.yield_forecast = 45.5
        forecast.monthly_risk = {
            "April": RiskLevel.GREEN,
            "May": RiskLevel.YELLOW,
            "June": RiskLevel.RED,
        }
        
        msg = format_forecast_result(forecast)
        
        assert "прогноз готов" in msg.lower()
        assert "Юг" in msg
        assert "Озимая пшеница" in msg
        assert "45.5" in msg
        assert "ц/га" in msg

    def test_format_forecast_result_without_menu(self):
        """Тест результата прогноза без меню."""
        forecast = MagicMock(spec=SeasonForecast)
        forecast.zone = AgriculturalZone.AZOV
        forecast.crop_type = CropType.CORN
        forecast.sowing_date = datetime(2024, 5, 1)
        forecast.harvest_date = datetime(2024, 9, 1)
        forecast.yield_forecast = 80.0
        forecast.monthly_risk = {
            "June": RiskLevel.GREEN,
            "July": RiskLevel.GREEN,
        }
        
        msg = format_forecast_result(forecast, show_menu=False)
        
        assert "прогноз готов" in msg.lower()
        assert "сохранён" not in msg.lower()

    def test_format_forecast_saved(self):
        """Тест сообщения о сохранённом прогнозе."""
        msg = format_forecast_saved()
        
        assert "сохранён" in msg.lower()


class TestChartMessages:
    """Тесты для сообщений связанных с графиками."""

    def test_format_chart_generating(self):
        """Тест сообщения о генерации графика."""
        msg = format_chart_generating()
        
        assert "график" in msg.lower()
        assert "генер" in msg.lower()

    def test_format_chart_caption_timeline(self):
        """Тест подписи графика временной шкалы."""
        msg = format_chart_caption_timeline()
        
        assert "динамика" in msg.lower()
        assert "урожай" in msg.lower()

    def test_format_chart_caption_monthly(self):
        """Тест подписи месячного графика."""
        msg = format_chart_caption_monthly()
        
        assert "риск" in msg.lower()
        assert "ежемесячн" in msg.lower()

    def test_format_new_forecast_button(self):
        """Тест сообщения кнопки нового прогноза."""
        msg = format_new_forecast_button()
        
        assert "новый прогноз" in msg.lower()


class TestMyForecastsMessages:
    """Тесты для сообщений моих прогнозов."""

    def test_format_my_forecasts_header(self):
        """Тест заголовка моих прогнозов."""
        msg = format_my_forecasts_header(5)
        
        assert "прогноз" in msg.lower()
        assert "5" in msg

    def test_format_forecast_list_item(self):
        """Тест формата элемента списка прогнозов."""
        # Создаём мок прогноза
        forecast = MagicMock()
        forecast.overall_risk = "green"
        forecast.sowing_date = datetime(2024, 4, 1)
        forecast.harvest_date = datetime(2024, 7, 15)
        forecast.zone_display = "Юг"
        forecast.crop_display = "Озимая пшеница"
        forecast.yield_forecast = 45.5
        
        msg = format_forecast_list_item(forecast, 1)
        
        assert "1." in msg
        assert "Юг" in msg
        assert "Озимая пшеница" in msg
        assert "45.5" in msg

    def test_format_no_forecasts(self):
        """Тест сообщения об отсутствии прогнозов."""
        msg = format_no_forecasts()
        
        assert "нет" in msg.lower() or "пока нет" in msg.lower()
        assert "/predict" in msg


class TestCropsAndRegionsMessages:
    """Тесты для сообщений о культурах и регионах."""

    def test_format_crops_list(self):
        """Тест сообщения списка культур."""
        msg = format_crops_list()
        
        assert "культур" in msg.lower()

    def test_format_crop_detail(self):
        """Тест сообщения деталей культуры."""
        msg = format_crop_detail(CropType.WINTER_WHEAT)
        
        assert "пшеница" in msg.lower()
        assert "вегетация" in msg.lower()

    def test_format_regions_list(self):
        """Тест сообщения списка регионов."""
        msg = format_regions_list()
        
        assert "зоны" in msg.lower() or "регион" in msg.lower()

    def test_format_region_detail(self):
        """Тест сообщения деталей региона."""
        msg = format_region_detail(AgriculturalZone.SOUTH)
        
        assert "ростов" in msg.lower()
        assert "климат" in msg.lower()


class TestForecastDetailFormatting:
    """Тесты для форматирования деталей прогноза."""

    def test_format_forecast_detail(self):
        """Тест детального просмотра прогноза."""
        # Создаём мок прогноза
        forecast = MagicMock()
        forecast.id = 1
        forecast.zone_display = "Юг"
        forecast.crop_display = "Озимая пшеница"
        forecast.sowing_date = datetime(2024, 4, 1)
        forecast.harvest_date = datetime(2024, 7, 15)
        forecast.yield_forecast = 45.5
        forecast.overall_risk = "green"
        forecast.created_at = datetime(2024, 4, 1, 12, 0)
        
        monthly_risk = {"May": "green", "June": "yellow"}
        
        msg = format_forecast_detail(forecast, monthly_risk)
        
        assert "прогноз" in msg.lower()
        assert "Юг" in msg
        assert "45.5" in msg
