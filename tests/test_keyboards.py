"""Тесты для генерации клавиатур."""
import pytest

from src.bot.keyboards import (
    get_crop_keyboard,
    get_crops_list_keyboard,
    get_forecast_actions_keyboard,
    get_main_menu_keyboard,
    get_main_reply_keyboard,
    get_myforecasts_keyboard,
    get_new_forecast_keyboard,
    get_regions_list_keyboard,
    get_stage_keyboard,
    get_yes_no_keyboard,
    get_zone_keyboard,
)
from src.ml.dataset.schemas import AgriculturalZone, CropType, GrowingStage


class TestReplyKeyboard:
    """Тесты для reply клавиатуры."""

    def test_get_main_reply_keyboard(self):
        """Тест генерации главной reply клавиатуры."""
        keyboard = get_main_reply_keyboard()
        
        assert keyboard is not None
        assert keyboard.resize_keyboard is True
        assert keyboard.one_time_keyboard is False
        
        # Проверяем наличие кнопок
        button_texts = []
        for row in keyboard.keyboard:
            for button in row:
                button_texts.append(button.text)
        
        assert "🌾 Новый прогноз" in button_texts
        assert "📋 Мои прогнозы" in button_texts
        assert "🌻 О культурах" in button_texts
        assert "🗺️ О регионах" in button_texts
        assert "❓ Помощь" in button_texts


class TestMainMenuKeyboard:
    """Тесты для главного меню inline клавиатуры."""

    def test_get_main_menu_keyboard(self):
        """Тест генерации клавиатуры главного меню."""
        keyboard = get_main_menu_keyboard()
        
        assert keyboard is not None
        
        # Проверяем данные callback
        callback_datas = []
        for row in keyboard.inline_keyboard:
            for btn in row:
                callback_datas.append(btn.callback_data)
        
        assert "cmd:predict" in callback_datas
        assert "cmd:myforecasts" in callback_datas
        assert "cmd:crops" in callback_datas
        assert "cmd:regions" in callback_datas
        assert "cmd:help" in callback_datas


class TestZoneKeyboard:
    """Тесты для клавиатуры выбора зоны."""

    def test_get_zone_keyboard(self):
        """Тест генерации клавиатуры зон."""
        keyboard = get_zone_keyboard()
        
        assert keyboard is not None
        
        # Проверяем наличие всех зон
        zones_found = []
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data.startswith("zone:"):
                    zones_found.append(button.callback_data)
        
        assert len(zones_found) == len(AgriculturalZone)
        
        # Проверяем кнопку назад
        back_found = False
        for row in keyboard.inline_keyboard:
            for button in row:
                if "назад" in button.text.lower():
                    back_found = True
        assert back_found


class TestCropKeyboard:
    """Тесты для клавиатуры выбора культуры."""

    def test_get_crop_keyboard(self):
        """Тест генерации клавиатуры культур."""
        keyboard = get_crop_keyboard()
        
        assert keyboard is not None
        
        # Проверяем наличие всех культур
        crops_found = []
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data.startswith("crop:"):
                    crops_found.append(button.callback_data)
        
        assert len(crops_found) == len(CropType)


class TestRegionsListKeyboard:
    """Тесты для клавиатуры списка регионов."""

    def test_get_regions_list_keyboard(self):
        """Тест клавиатуры списка регионов."""
        keyboard = get_regions_list_keyboard()
        
        assert keyboard is not None
        
        # Проверяем наличие всех зон
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data.startswith("region:"):
                    assert button.callback_data in [f"region:{z.value}" for z in AgriculturalZone]


class TestCropsListKeyboard:
    """Тесты для клавиатуры списка культур."""

    def test_get_crops_list_keyboard(self):
        """Тест клавиатуры списка культур."""
        keyboard = get_crops_list_keyboard()
        
        assert keyboard is not None
        
        # Проверяем наличие всех культур
        crops_found = []
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data.startswith("crop_info:"):
                    crops_found.append(button.callback_data)
        
        assert len(crops_found) == len(CropType)


class TestForecastKeyboards:
    """Тесты для клавиатур связанных с прогнозами."""

    def test_get_forecast_actions_keyboard(self):
        """Тест клавиатуры действий прогноза."""
        keyboard = get_forecast_actions_keyboard(123)
        
        assert keyboard is not None
        
        # Проверяем кнопки с ID прогноза
        callback_datas = []
        for row in keyboard.inline_keyboard:
            for button in row:
                callback_datas.append(button.callback_data)
        
        assert "forecast:charts:123" in callback_datas
        assert "forecast:delete:123" in callback_datas

    def test_get_myforecasts_keyboard_no_pagination(self):
        """Тест клавиатуры моих прогнозов без пагинации."""
        keyboard = get_myforecasts_keyboard(count=3, page=0)
        
        assert keyboard is not None
        
        # Должно быть 3 кнопки прогнозов + кнопка назад
        buttons_count = sum(len(row) for row in keyboard.inline_keyboard)
        assert buttons_count >= 4  # 3 прогноза + назад

    def test_get_myforecasts_keyboard_with_pagination(self):
        """Тест клавиатуры моих прогнозов с пагинацией."""
        keyboard = get_myforecasts_keyboard(count=10, page=0)
        
        assert keyboard is not None
        
        # Проверяем кнопки пагинации
        callback_datas = []
        for row in keyboard.inline_keyboard:
            for button in row:
                callback_datas.append(button.callback_data)
        
        # Должна быть кнопка "Вперёд"
        assert any("вперёд" in cb.lower() or "page:" in cb for cb in callback_datas)

    def test_get_myforecasts_keyboard_middle_page(self):
        """Тест клавиатуры моих прогнозов на средней странице."""
        keyboard = get_myforecasts_keyboard(count=10, page=1)
        
        assert keyboard is not None
        
        # Должны быть и назад и вперёд
        callback_datas = []
        for row in keyboard.inline_keyboard:
            for button in row:
                callback_datas.append(button.callback_data)
        
        assert any("page:" in cb for cb in callback_datas)

    def test_get_new_forecast_keyboard(self):
        """Тест клавиатуры нового прогноза."""
        keyboard = get_new_forecast_keyboard()
        
        assert keyboard is not None
        
        # Проверяем кнопки
        callback_datas = []
        for row in keyboard.inline_keyboard:
            for button in row:
                callback_datas.append(button.callback_data)
        
        assert "cmd:show_charts" in callback_datas
        assert "cmd:predict" in callback_datas
        assert "cmd:back_to_menu" in callback_datas


class TestStageKeyboard:
    """Тесты для клавиатуры выбора стадии."""

    def test_get_stage_keyboard(self):
        """Тест генерации клавиатуры стадий."""
        keyboard = get_stage_keyboard()
        
        assert keyboard is not None
        
        # Проверяем наличие всех стадий
        stages_found = []
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data.startswith("stage:"):
                    stages_found.append(button.callback_data)
        
        assert len(stages_found) == len(GrowingStage)


class TestYesNoKeyboard:
    """Тесты для клавиатуры да/нет."""

    def test_get_yes_no_keyboard(self):
        """Тест генерации клавиатуры да/нет."""
        keyboard = get_yes_no_keyboard("test_action")
        
        assert keyboard is not None
        
        # Проверяем кнопки
        callback_datas = []
        for row in keyboard.inline_keyboard:
            for button in row:
                callback_datas.append(button.callback_data)
        
        assert "test_action:yes" in callback_datas
        assert "test_action:no" in callback_datas
