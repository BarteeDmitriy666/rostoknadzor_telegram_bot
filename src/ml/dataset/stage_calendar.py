"""Календарь стадий культур и калькулятор даты уборки."""
from datetime import datetime, timedelta

from src.ml.dataset.schemas import AgriculturalZone, CropType, GrowingStage


# Дни от посева до каждой стадии (диапазоны)
# Основано на типичных сельскохозяйственных календарях для Ростовской области
CROP_STAGE_DAYS = {
    # Зерновые и бобовые
    CropType.WINTER_WHEAT: {
        GrowingStage.SOWING: (0, 0),
        GrowingStage.EMERGENCE: (10, 14),
        GrowingStage.TILLERING: (25, 35),
        GrowingStage.BOOTING: (120, 140),  # Весеннее отрастание
        GrowingStage.HEADING_FLOWERING: (150, 170),
        GrowingStage.RIPENING_MATURITY: (200, 230),
    },
    CropType.SPRING_BARLEY: {
        GrowingStage.SOWING: (0, 0),
        GrowingStage.EMERGENCE: (8, 12),
        GrowingStage.TILLERING: (20, 30),
        GrowingStage.BOOTING: (45, 55),
        GrowingStage.HEADING_FLOWERING: (60, 75),
        GrowingStage.RIPENING_MATURITY: (90, 110),
    },
    CropType.CORN: {
        GrowingStage.SOWING: (0, 0),
        GrowingStage.EMERGENCE: (12, 18),
        GrowingStage.TILLERING: (30, 40),
        GrowingStage.BOOTING: (55, 70),
        GrowingStage.HEADING_FLOWERING: (70, 90),
        GrowingStage.RIPENING_MATURITY: (120, 150),
    },
    CropType.OATS: {
        GrowingStage.SOWING: (0, 0),
        GrowingStage.EMERGENCE: (8, 12),
        GrowingStage.TILLERING: (20, 28),
        GrowingStage.BOOTING: (40, 50),
        GrowingStage.HEADING_FLOWERING: (55, 70),
        GrowingStage.RIPENING_MATURITY: (85, 100),
    },
    CropType.RYE: {
        GrowingStage.SOWING: (0, 0),
        GrowingStage.EMERGENCE: (10, 14),
        GrowingStage.TILLERING: (25, 35),
        GrowingStage.BOOTING: (130, 150),
        GrowingStage.HEADING_FLOWERING: (155, 175),
        GrowingStage.RIPENING_MATURITY: (195, 220),
    },
    CropType.MILLET: {
        GrowingStage.SOWING: (0, 0),
        GrowingStage.EMERGENCE: (6, 10),
        GrowingStage.TILLERING: (18, 25),
        GrowingStage.BOOTING: (35, 45),
        GrowingStage.HEADING_FLOWERING: (50, 65),
        GrowingStage.RIPENING_MATURITY: (75, 95),
    },
    CropType.SORGHUM: {
        GrowingStage.SOWING: (0, 0),
        GrowingStage.EMERGENCE: (10, 15),
        GrowingStage.TILLERING: (25, 35),
        GrowingStage.BOOTING: (50, 65),
        GrowingStage.HEADING_FLOWERING: (65, 85),
        GrowingStage.RIPENING_MATURITY: (100, 130),
    },
    CropType.PEAS: {
        GrowingStage.SOWING: (0, 0),
        GrowingStage.EMERGENCE: (7, 12),
        GrowingStage.TILLERING: (20, 30),
        GrowingStage.BOOTING: (35, 45),
        GrowingStage.HEADING_FLOWERING: (45, 60),
        GrowingStage.RIPENING_MATURITY: (70, 90),
    },
    CropType.CHICKPEAS: {
        GrowingStage.SOWING: (0, 0),
        GrowingStage.EMERGENCE: (8, 14),
        GrowingStage.TILLERING: (22, 32),
        GrowingStage.BOOTING: (40, 55),
        GrowingStage.HEADING_FLOWERING: (55, 70),
        GrowingStage.RIPENING_MATURITY: (85, 110),
    },
    # Промышленные и масличные культуры
    CropType.SUNFLOWER: {
        GrowingStage.SOWING: (0, 0),
        GrowingStage.EMERGENCE: (10, 15),
        GrowingStage.TILLERING: (25, 35),
        GrowingStage.BOOTING: (50, 65),
        GrowingStage.HEADING_FLOWERING: (65, 80),
        GrowingStage.RIPENING_MATURITY: (95, 120),
    },
    CropType.SUGAR_BEET: {
        GrowingStage.SOWING: (0, 0),
        GrowingStage.EMERGENCE: (12, 18),
        GrowingStage.TILLERING: (35, 50),
        GrowingStage.BOOTING: (70, 90),
        GrowingStage.HEADING_FLOWERING: (120, 150),
        GrowingStage.RIPENING_MATURITY: (160, 200),
    },
    CropType.SOYBEANS: {
        GrowingStage.SOWING: (0, 0),
        GrowingStage.EMERGENCE: (6, 10),
        GrowingStage.TILLERING: (20, 30),
        GrowingStage.BOOTING: (40, 55),
        GrowingStage.HEADING_FLOWERING: (55, 70),
        GrowingStage.RIPENING_MATURITY: (90, 120),
    },
    CropType.FLAX: {
        GrowingStage.SOWING: (0, 0),
        GrowingStage.EMERGENCE: (8, 12),
        GrowingStage.TILLERING: (20, 30),
        GrowingStage.BOOTING: (35, 50),
        GrowingStage.HEADING_FLOWERING: (50, 65),
        GrowingStage.RIPENING_MATURITY: (75, 95),
    },
    CropType.MUSTARD: {
        GrowingStage.SOWING: (0, 0),
        GrowingStage.EMERGENCE: (5, 8),
        GrowingStage.TILLERING: (15, 25),
        GrowingStage.BOOTING: (30, 40),
        GrowingStage.HEADING_FLOWERING: (40, 55),
        GrowingStage.RIPENING_MATURITY: (60, 80),
    },
    # Овощи и фрукты
    CropType.POTATOES: {
        GrowingStage.SOWING: (0, 0),
        GrowingStage.EMERGENCE: (15, 25),
        GrowingStage.TILLERING: (35, 50),
        GrowingStage.BOOTING: (55, 70),
        GrowingStage.HEADING_FLOWERING: (70, 90),
        GrowingStage.RIPENING_MATURITY: (90, 120),
    },
    CropType.TOMATOES: {
        GrowingStage.SOWING: (0, 0),
        GrowingStage.EMERGENCE: (7, 12),
        GrowingStage.TILLERING: (25, 35),
        GrowingStage.BOOTING: (45, 60),
        GrowingStage.HEADING_FLOWERING: (60, 80),
        GrowingStage.RIPENING_MATURITY: (85, 115),
    },
    CropType.ONIONS: {
        GrowingStage.SOWING: (0, 0),
        GrowingStage.EMERGENCE: (10, 15),
        GrowingStage.TILLERING: (30, 45),
        GrowingStage.BOOTING: (60, 80),
        GrowingStage.HEADING_FLOWERING: (80, 100),
        GrowingStage.RIPENING_MATURITY: (100, 130),
    },
    CropType.APPLES: {
        GrowingStage.SOWING: (0, 0),
        GrowingStage.EMERGENCE: (15, 20),
        GrowingStage.TILLERING: (40, 55),
        GrowingStage.BOOTING: (80, 100),
        GrowingStage.HEADING_FLOWERING: (100, 120),
        GrowingStage.RIPENING_MATURITY: (150, 180),
    },
    CropType.PLUMS: {
        GrowingStage.SOWING: (0, 0),
        GrowingStage.EMERGENCE: (12, 18),
        GrowingStage.TILLERING: (35, 50),
        GrowingStage.BOOTING: (65, 85),
        GrowingStage.HEADING_FLOWERING: (85, 105),
        GrowingStage.RIPENING_MATURITY: (130, 160),
    },
    CropType.GRAPES: {
        GrowingStage.SOWING: (0, 0),
        GrowingStage.EMERGENCE: (18, 25),
        GrowingStage.TILLERING: (45, 60),
        GrowingStage.BOOTING: (90, 115),
        GrowingStage.HEADING_FLOWERING: (115, 140),
        GrowingStage.RIPENING_MATURITY: (160, 200),
    },
}


def get_stage_date(sowing_date: datetime, crop: CropType, stage: GrowingStage) -> datetime:
    """
    Рассчитывает ожидаемую дату для конкретной стадии роста.
    
    Args:
        sowing_date: Дата посева
        crop: Тип культуры
        stage: Целевая стадия роста
    
    Returns:
        Ожидаемая дата для стадии (середина диапазона)
    """
    days_range = CROP_STAGE_DAYS[crop][stage]
    days = (days_range[0] + days_range[1]) // 2
    return sowing_date + timedelta(days=days)


def get_harvest_date(sowing_date: datetime, crop: CropType) -> datetime:
    """
    Рассчитывает ожидаемую дату уборки на основе даты посева и культуры.
    
    Args:
        sowing_date: Дата посева
        crop: Тип культуры
    
    Returns:
        Ожидаемая дата уборки
    """
    return get_stage_date(sowing_date, crop, GrowingStage.RIPENING_MATURITY)


def get_current_stage(
    sowing_date: datetime,
    crop: CropType,
    current_date: datetime,
) -> tuple[GrowingStage, datetime, datetime]:
    """
    Определяет текущую стадию роста на основе дат.
    
    Args:
        sowing_date: Дата посева
        crop: Тип культуры
        current_date: Текущая дата
    
    Returns:
        Кортеж из (текущая_стадия, дата_начала_стадии, дата_конца_стадии)
    """
    stages = list(GrowingStage)
    
    for i, stage in enumerate(stages):
        stage_start = get_stage_date(sowing_date, crop, stage)
        
        # Начало следующей стадии (или далёкое будущее для последней стадии)
        if i + 1 < len(stages):
            next_stage = stages[i + 1]
            stage_end = get_stage_date(sowing_date, crop, next_stage)
        else:
            stage_end = stage_start + timedelta(days=60)  # Принимаем 60 дней для последней стадии
        
        if stage_start <= current_date < stage_end:
            return stage, stage_start, stage_end
        
        if current_date < stage_start:
            return GrowingStage.SOWING, sowing_date, stage_start
    
    # После даты уборки
    last_stage_date = get_stage_date(sowing_date, crop, GrowingStage.RIPENING_MATURITY)
    return GrowingStage.RIPENING_MATURITY, last_stage_date, last_stage_date + timedelta(days=30)


def calculate_season_timeline(
    sowing_date: datetime,
    crop: CropType,
    zone: AgriculturalZone,  # для будущих корректировок
) -> list[dict]:
    """
    Рассчитывает полную временную шкалу сезона с датами для всех стадий.
    
    Args:
        sowing_date: Дата посева
        crop: Тип культуры
        zone: Сельскохозяйственная зона (зарезервировано для будущего использования)
    
    Returns:
        Список словарей с информацией о стадиях
    """
    stages_list = list(GrowingStage)
    harvest_date = get_harvest_date(sowing_date, crop)
    timeline = []
    
    for stage in stages_list:
        start_date = get_stage_date(sowing_date, crop, stage)
        
        # Рассчитываем дату окончания и продолжительность
        if stage == GrowingStage.RIPENING_MATURITY:
            end_date = harvest_date
            duration = (harvest_date - get_stage_date(sowing_date, crop, GrowingStage.HEADING_FLOWERING)).days
        else:
            idx = stages_list.index(stage)
            next_stage = stages_list[idx + 1]
            end_date = get_stage_date(sowing_date, crop, next_stage)
            duration = (end_date - start_date).days
        
        timeline.append({
            "stage": stage,
            "start_date": start_date,
            "end_date": end_date,
            "duration_days": duration,
        })
    
    return timeline