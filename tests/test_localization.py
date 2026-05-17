"""Тесты для модуля русской локализации."""
import pytest

from src.bot.localization import (
    CROP_DESCRIPTIONS,
    CROP_DISPLAY,
    RISK_DISPLAY,
    RISK_TEXT,
    RISK_LABELS,
    STAGE_DESCRIPTIONS,
    STAGE_DISPLAY,
    ZONE_DESCRIPTIONS,
    ZONE_DISPLAY,
    format_crop_display,
    format_stage_display,
    format_zone_display,
    get_crop_description,
    get_stage_description,
    get_zone_description,
)
from src.ml.dataset.schemas import AgriculturalZone, CropType, GrowingStage, RiskLevel


class TestZoneLocalization:
    """Тесты для локализации зон."""

    def test_zone_display_all_zones(self):
        """Тест наличия отображаемых имён для всех зон."""
        for zone in AgriculturalZone:
            display = ZONE_DISPLAY.get(zone)
            assert display is not None
            assert len(display) > 0

    def test_zone_descriptions_all_zones(self):
        """Тест наличия описаний для всех зон."""
        for zone in AgriculturalZone:
            desc = ZONE_DESCRIPTIONS.get(zone)
            assert desc is not None
            assert len(desc) > 0

    def test_format_zone_display(self):
        """Тест функции format_zone_display."""
        assert format_zone_display(AgriculturalZone.SOUTH) == "Юг"
        assert format_zone_display(AgriculturalZone.AZOV) == "Азов"
        assert format_zone_display(AgriculturalZone.NORTHWEST) == "Северо-Запад"

    def test_get_zone_description(self):
        """Тест функции get_zone_description."""
        desc = get_zone_description(AgriculturalZone.SOUTH)
        assert "Ростовской области" in desc
        assert "климат" in desc.lower()

    def test_zone_display_format(self):
        """Тест что названия зон на русском языке."""
        expected_zones = {
            AgriculturalZone.NORTHWEST: "Северо-Запад",
            AgriculturalZone.NORTHEAST: "Северо-Восток",
            AgriculturalZone.CENTRAL_IRRIGATED: "Центральный Орошаемый",
            AgriculturalZone.AZOV: "Азов",
            AgriculturalZone.SOUTH: "Юг",
            AgriculturalZone.EAST: "Восток",
        }
        
        for zone, expected in expected_zones.items():
            assert format_zone_display(zone) == expected


class TestCropLocalization:
    """Тесты для локализации культур."""

    def test_crop_display_all_crops(self):
        """Тест наличия отображаемых имён для всех культур."""
        for crop in CropType:
            display = CROP_DISPLAY.get(crop)
            assert display is not None
            assert len(display) > 0

    def test_crop_descriptions_all_crops(self):
        """Тест наличия описаний для всех культур."""
        for crop in CropType:
            desc = CROP_DESCRIPTIONS.get(crop)
            assert desc is not None
            assert len(desc) > 0

    def test_format_crop_display(self):
        """Тест функции format_crop_display."""
        assert format_crop_display(CropType.WINTER_WHEAT) == "Озимая пшеница"
        assert format_crop_display(CropType.CORN) == "Кукуруза"
        assert format_crop_display(CropType.SUNFLOWER) == "Подсолнечник"

    def test_get_crop_description(self):
        """Тест функции get_crop_description."""
        desc = get_crop_description(CropType.WINTER_WHEAT)
        assert "пшеница" in desc.lower()
        assert "вегетация" in desc.lower()

    def test_crop_display_format(self):
        """Тест что названия культур на русском языке."""
        expected_crops = {
            CropType.WINTER_WHEAT: "Озимая пшеница",
            CropType.SPRING_BARLEY: "Яровой ячмень",
            CropType.CORN: "Кукуруза",
            CropType.OATS: "Овёс",
            CropType.RYE: "Рожь",
            CropType.MILLET: "Просо",
            CropType.SORGHUM: "Сорго",
            CropType.PEAS: "Горох",
            CropType.CHICKPEAS: "Нут",
            CropType.SUNFLOWER: "Подсолнечник",
            CropType.SUGAR_BEET: "Сахарная свёкла",
            CropType.SOYBEANS: "Соевые бобы",
            CropType.FLAX: "Лён",
            CropType.MUSTARD: "Горчица",
            CropType.POTATOES: "Картофель",
            CropType.TOMATOES: "Томаты",
            CropType.ONIONS: "Лук",
            CropType.APPLES: "Яблоки",
            CropType.PLUMS: "Сливы",
            CropType.GRAPES: "Виноград",
        }
        
        for crop, expected in expected_crops.items():
            assert format_crop_display(crop) == expected


class TestStageLocalization:
    """Тесты для локализации стадий роста."""

    def test_stage_display_all_stages(self):
        """Тест наличия отображаемых имён для всех стадий."""
        for stage in GrowingStage:
            display = STAGE_DISPLAY.get(stage)
            assert display is not None
            assert len(display) > 0

    def test_stage_descriptions_all_stages(self):
        """Тест наличия описаний для всех стадий."""
        for stage in GrowingStage:
            desc = STAGE_DESCRIPTIONS.get(stage)
            assert desc is not None
            assert len(desc) > 0

    def test_format_stage_display(self):
        """Тест функции format_stage_display."""
        assert format_stage_display(GrowingStage.SOWING) == "Посев"
        assert format_stage_display(GrowingStage.EMERGENCE) == "Всходы"
        assert format_stage_display(GrowingStage.TILLERING) == "Кущение"
        assert format_stage_display(GrowingStage.BOOTING) == "Выход в трубку"
        assert format_stage_display(GrowingStage.HEADING_FLOWERING) == "Цветение"
        assert format_stage_display(GrowingStage.RIPENING_MATURITY) == "Созревание"

    def test_get_stage_description(self):
        """Тест функции get_stage_description."""
        desc = get_stage_description(GrowingStage.SOWING)
        assert "посев" in desc.lower()


class TestRiskLocalization:
    """Тесты для локализации уровней риска."""

    def test_risk_display_all_levels(self):
        """Тест наличия отображаемых имён для всех уровней риска."""
        for risk in RiskLevel:
            display = RISK_DISPLAY.get(risk)
            assert display is not None
            assert len(display) > 0

    def test_risk_text_all_levels(self):
        """Тест наличия текстовых представлений для всех уровней риска."""
        for risk in RiskLevel:
            text = RISK_TEXT.get(risk)
            assert text is not None
            assert len(text) > 0

    def test_risk_labels_all_levels(self):
        """Тест наличия меток для всех уровней риска."""
        for risk in RiskLevel:
            label = RISK_LABELS.get(risk)
            assert label is not None
            assert len(label) > 0

    def test_risk_display_format(self):
        """Тест что отображаемый риск содержит эмодзи и текст."""
        assert "Низкий" in RISK_DISPLAY[RiskLevel.GREEN]
        assert "Средний" in RISK_DISPLAY[RiskLevel.YELLOW]
        assert "Высокий" in RISK_DISPLAY[RiskLevel.RED]

    def test_risk_text_format(self):
        """Тест формата текста риска."""
        assert RISK_TEXT[RiskLevel.GREEN] == "низкий"
        assert RISK_TEXT[RiskLevel.YELLOW] == "средний"
        assert RISK_TEXT[RiskLevel.RED] == "высокий"

    def test_risk_labels_format(self):
        """Тест формата меток риска."""
        assert RISK_LABELS[RiskLevel.GREEN] == "НИЗКИЙ"
        assert RISK_LABELS[RiskLevel.YELLOW] == "СРЕДНИЙ"
        assert RISK_LABELS[RiskLevel.RED] == "ВЫСОКИЙ"


class TestLocalizationCompleteness:
    """Тесты для полноты данных локализации."""

    def test_all_zones_localized(self):
        """Проверка что все значения AgriculturalZone имеют локализацию."""
        for zone in AgriculturalZone:
            assert zone in ZONE_DISPLAY, f"Missing display for {zone}"
            assert zone in ZONE_DESCRIPTIONS, f"Missing description for {zone}"

    def test_all_crops_localized(self):
        """Проверка что все значения CropType имеют локализацию."""
        for crop in CropType:
            assert crop in CROP_DISPLAY, f"Missing display for {crop}"
            assert crop in CROP_DESCRIPTIONS, f"Missing description for {crop}"

    def test_all_stages_localized(self):
        """Проверка что все значения GrowingStage имеют локализацию."""
        for stage in GrowingStage:
            assert stage in STAGE_DISPLAY, f"Missing display for {stage}"
            assert stage in STAGE_DESCRIPTIONS, f"Missing description for {stage}"

    def test_all_risks_localized(self):
        """Проверка что все значения RiskLevel имеют локализацию."""
        for risk in RiskLevel:
            assert risk in RISK_DISPLAY, f"Missing display for {risk}"
            assert risk in RISK_TEXT, f"Missing text for {risk}"
            assert risk in RISK_LABELS, f"Missing label for {risk}"
