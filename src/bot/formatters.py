"""Форматтеры сообщений для ответов бота - чистый формат."""
from datetime import datetime

from src.bot.localization import (
    RISK_DISPLAY,
    RISK_EMOJI,
    RISK_LABELS,
    STAGE_DISPLAY,
    format_crop_display,
    format_zone_display,
    get_crop_description,
    get_zone_description,
    translate_month,
)
from src.ml.dataset.schemas import (
    AgriculturalZone,
    CropType,
    GrowingStage,
    RiskLevel,
    SeasonForecast,
)


def format_start_message() -> str:
    """Форматирует приветственное сообщение с главным меню."""
    return """🤖 <b>АгроБот - Прогноз Урожайности</b>

Я помогу вам получить прогноз урожайности и риска заболеваний для сельскохозяйственных культур в Ростовской области.

<b>Выберите действие:</b>"""


def format_help_message() -> str:
    """Форматирует справочное сообщение."""
    return """📖 <b>Справка</b>

<b>Как получить прогноз:</b>
1. Нажмите /predict
2. Выберите регион
3. Выберите культуру
4. Введите дату посева
5. Получите прогноз с графиками!

<b>Доступные команды:</b>
• /predict — Новый прогноз
• /myforecasts — Мои прогнозы
• /crops — О культурах
• /regions — О регионах
• /help — Справка

<b>Риск заболеваний:</b>
🟢 Низкий  |  🟡 Средний  |  🔴 Высокий"""


def format_cancel_message() -> str:
    """Форматирует сообщение об отмене."""
    return "❌ Действие отменено."


def format_error_message(error: str) -> str:
    """Форматирует сообщение об ошибке."""
    return f"❌ <b>Ошибка:</b> {error}"


def format_zone_selection() -> str:
    """Форматирует приглашение выбора зоны."""
    return """📍 <b>Выберите регион</b>

Выберите сельскохозяйственную зону Ростовской области."""


def format_crop_selection(zone: AgriculturalZone) -> str:
    """Форматирует приглашение выбора культуры."""
    zone_display = format_zone_display(zone)
    return f"""🌾 <b>Выберите культуру</b>

Регион: <b>{zone_display}</b>"""


def format_sowing_date_prompt(zone: AgriculturalZone, crop: CropType) -> str:
    """Форматирует приглашение ввода даты посева."""
    zone_display = format_zone_display(zone)
    crop_display = format_crop_display(crop)
    today = datetime.now().strftime("%d.%m.%Y")
    return f"""📅 <b>Введите дату посева</b>

Регион: {zone_display}
Культура: {crop_display}

Введите дату в формате <code>ДД.ММ.ГГГГ</code>
<i>Например: {today}</i>"""


def format_forecast_result(
    forecast: SeasonForecast,
    show_menu: bool = True,
) -> str:
    """Форматирует полный результат прогноза с чистой разметкой."""
    zone_display = format_zone_display(forecast.zone)
    crop_display = format_crop_display(forecast.crop_type)
    
    # Расчёт общего риска
    all_risks = list(forecast.monthly_risk.values())
    if RiskLevel.RED in all_risks:
        overall_risk = RiskLevel.RED
    elif RiskLevel.YELLOW in all_risks:
        overall_risk = RiskLevel.YELLOW
    else:
        overall_risk = RiskLevel.GREEN
    
    # Формирование отображения месячного риска
    monthly_lines = []
    for month, risk in forecast.monthly_risk.items():
        month_ru = translate_month(month)
        monthly_lines.append(f"  {month_ru}: {RISK_DISPLAY[risk]}")
    
    monthly_summary = "\n".join(monthly_lines) if monthly_lines else "  Нет данных"
    
    # Дней до уборки
    days_to_harvest = (forecast.harvest_date - forecast.sowing_date).days
    
    result = f"""📊 <b>Прогноз готов!</b>

<b>Параметры:</b>
  🌍 Регион: {zone_display}
  🌾 Культура: {crop_display}
  📅 Посев: {forecast.sowing_date.strftime('%d.%m.%Y')}

<b>Урожай:</b>
  📅 Дата уборки: {forecast.harvest_date.strftime('%d.%m.%Y')}
  ⏱️ Дней до уборки: {days_to_harvest}
  🌾 Урожайность: <b>{forecast.yield_forecast:.1f}</b> ц/га

<b>Риск заболеваний:</b>
{monthly_summary}

<b>Общий риск:</b> {RISK_DISPLAY[overall_risk]}"""
    
    if show_menu:
        result += "\n\n<i>Прогноз сохранён в вашу историю.</i>"
    
    return result


def format_forecast_saved() -> str:
    """Форматирует сообщение о сохранённом прогнозе."""
    return "✅ Прогноз сохранён в историю."


def format_chart_generating() -> str:
    """Форматирует сообщение о генерации графиков."""
    return "📊 Генерирую графики..."


def format_chart_caption_timeline() -> str:
    """Подпись для графика временной шкалы."""
    return "📈 Динамика урожайности и риска заболеваний"


def format_chart_caption_monthly() -> str:
    """Подпись для месячного графика."""
    return "📅 Ежемесячный риск заболеваний"


def format_new_forecast_button() -> str:
    """Сообщение с приглашением нового прогноза."""
    return "🔄 <b>Новый прогноз</b>"


def format_my_forecasts_header(count: int) -> str:
    """Форматирует заголовок списка моих прогнозов."""
    return f"📋 <b>Мои прогнозы</b> ({count} шт.)"


def format_forecast_list_item(
    forecast,
    index: int,
) -> str:
    """Форматирует один прогноз в списке."""
    emoji = RISK_EMOJI.get(forecast.overall_risk, "⚪")
    date_str = forecast.sowing_date.strftime("%d.%m.%Y")
    harvest_str = forecast.harvest_date.strftime("%d.%m.%Y")
    
    return f"""<b>{index}.</b> {forecast.zone_display} | {forecast.crop_display}
   📅 {date_str} → {harvest_str} | {emoji} {forecast.yield_forecast:.1f} ц/га"""


def format_no_forecasts() -> str:
    """Форматирует сообщение, когда у пользователя нет прогнозов."""
    return """📋 <b>Мои прогнозы</b>

У вас пока нет сохранённых прогнозов.

Нажмите /predict чтобы создать первый прогноз!"""


def format_forecast_detail(
    forecast,
    monthly_risk: dict,
) -> str:
    """Форматирует детальный вид прогноза."""
    emoji = RISK_EMOJI.get(forecast.overall_risk, "⚪")
    risk_display = RISK_DISPLAY.get(RiskLevel(forecast.overall_risk), emoji)
    
    # Формирование строк по месяцам
    monthly_lines = []
    for month, risk in monthly_risk.items():
        month_ru = translate_month(month)
        risk_text = RISK_LABELS.get(RiskLevel(risk), risk)
        monthly_lines.append(f"  {month_ru}: {risk_text}")
    
    days = (forecast.harvest_date - forecast.sowing_date).days
    
    return f"""📊 <b>Прогноз #{forecast.id}</b>

<b>Параметры:</b>
  🌍 Регион: {forecast.zone_display}
  🌾 Культура: {forecast.crop_display}
  📅 Посев: {forecast.sowing_date.strftime('%d.%m.%Y')}

<b>Урожай:</b>
  📅 Дата уборки: {forecast.harvest_date.strftime('%d.%m.%Y')}
  ⏱️ Дней: {days}
  🌾 Урожайность: <b>{forecast.yield_forecast:.1f}</b> ц/га

<b>Риск заболеваний:</b>
{chr(10).join(monthly_lines)}

{emoji} <b>Общий риск:</b> {risk_display}

<i>Создан: {forecast.created_at.strftime('%d.%m.%Y в %H:%M')}</i>"""


def format_crops_list() -> str:
    """Форматирует сообщение списка культур."""
    return """🌾 <b>Сельскохозяйственные культуры</b>

Выберите культуру для получения подробной информации."""


def format_crop_detail(crop: CropType) -> str:
    """Форматирует детальное описание культуры."""
    return get_crop_description(crop)


def format_regions_list() -> str:
    """Форматирует сообщение списка регионов."""
    return """🗺️ <b>Сельскохозяйственные зоны</b>

Выберите регион для получения подробной информации."""


def format_region_detail(zone: AgriculturalZone) -> str:
    """Форматирует детальное описание зоны."""
    return get_zone_description(zone)


def format_stage_short(stage: GrowingStage) -> str:
    """Форматирует краткое название стадии."""
    return STAGE_DISPLAY.get(stage, stage.value)
