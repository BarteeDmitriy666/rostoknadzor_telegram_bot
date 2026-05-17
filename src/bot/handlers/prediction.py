"""Обработчики разговоров предсказаний со всеми командами."""
import json
from datetime import datetime
from typing import Optional

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from loguru import logger

from src.bot.formatters import (
    format_cancel_message,
    format_crop_detail,
    format_crop_selection,
    format_forecast_detail,
    format_forecast_result,
    format_help_message,
    format_my_forecasts_header,
    format_no_forecasts,
    format_region_detail,
    format_regions_list,
    format_start_message,
    format_sowing_date_prompt,
    format_zone_selection,
    format_crops_list,
)
from src.bot.keyboards import (
    get_crop_keyboard,
    get_forecast_actions_keyboard,
    get_main_menu_keyboard,
    get_myforecasts_keyboard,
    get_new_forecast_keyboard,
    get_regions_list_keyboard,
    get_crops_list_keyboard,
    get_zone_keyboard,
)
from src.bot.states import PredictionStates
from src.bot.localization import (
    RISK_EMOJI,
    TOKEN_CONSUMED,
)
from src.payments.subscription import is_subscribed, consume_token, _is_monthly_active
from src.payments.repository import get_token_count
from src.bot.handlers.subscription import send_subscription_prompt
from src.ml.charts import generate_forecast_chart, generate_monthly_summary_chart
from src.ml.dataset.schemas import (
    AgriculturalZone,
    CropType,
    DiseaseForecast,
    GrowingStage,
    RiskLevel,
    SeasonForecast,
    StageInfo,
    WeatherInput,
)
from src.ml.forecast import forecast_season
from src.db.connection import get_or_create_user
from src.db.forecast_repository import (
    delete_forecast,
    get_forecast_by_id,
    get_user_forecasts,
    save_forecast,
    get_forecasts_count,
)

router = Router(name="prediction")


async def send_forecast_charts(
    message_or_callback: Message | CallbackQuery,
    forecast: SeasonForecast,
    reply_markup: Optional[object] = None,
) -> None:
    """
    Отправляет графики временной шкалы и месячные графики для прогноза.
    
    Args:
        message_or_callback: Сообщение или callback запрос для ответа
        forecast: SeasonForecast для генерации графиков
        reply_markup: Опциональная клавиатура для прикрепления
    """
    # Получает целевой объект сообщения (работает для Message и CallbackQuery)
    target = message_or_callback.message if hasattr(message_or_callback, 'message') else message_or_callback
    
    await message_or_callback.answer("📊 Генерирую графики...")
    
    # График временной шкалы
    chart_buf = generate_forecast_chart(forecast)
    chart_buf.seek(0)
    await target.answer_photo(
        photo=BufferedInputFile(chart_buf.getvalue(), filename="forecast_chart.png"),
        caption="📈 Динамика урожайности и риска заболеваний",
    )
    
    # Месячный график
    monthly_buf = generate_monthly_summary_chart(forecast)
    monthly_buf.seek(0)
    await target.answer_photo(
        photo=BufferedInputFile(monthly_buf.getvalue(), filename="monthly_risk.png"),
        caption="📅 Ежемесячный риск заболеваний",
    )
    
    # Показывает клавиатуру, если она предоставлена
    if reply_markup:
        await target.answer(
            "Выберите действие:",
            reply_markup=reply_markup,
        )


async def start_predict_flow(message: Message, state: FSMContext) -> None:
    """Запускает поток предсказания от команды /predict."""
    if message.from_user is None:
        return
    if not is_subscribed(message.from_user.id):
        logger.info("Predict flow denied: user={} not subscribed", message.from_user.id)
        await send_subscription_prompt(message, message.from_user.id)
        return
    logger.info("Predict flow started: user={}", message.from_user.id)
    await state.set_state(PredictionStates.waiting_for_zone)
    await state.update_data({})
    await message.answer(
        format_zone_selection(),
        parse_mode="HTML",
        reply_markup=get_zone_keyboard(),
    )


@router.callback_query(F.data == "cmd:predict")
async def cmd_predict_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Обрабатывает команду predict с клавиатуры."""
    if not is_subscribed(callback.from_user.id):
        if callback.message is not None:
            await send_subscription_prompt(callback.message, callback.from_user.id)
        await callback.answer()
        return
    await state.set_state(PredictionStates.waiting_for_zone)
    await state.update_data({})
    await callback.message.edit_text(
        format_zone_selection(),
        parse_mode="HTML",
        reply_markup=get_zone_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "cmd:myforecasts")
async def cmd_myforecasts_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Обрабатывает команду myforecasts с клавиатуры."""
    await show_user_forecasts(callback.message, callback.from_user.id, state)
    await callback.answer()


@router.callback_query(F.data == "cmd:crops")
async def cmd_crops_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Обрабатывает команду crops с клавиатуры."""
    await callback.message.edit_text(
        format_crops_list(),
        parse_mode="HTML",
        reply_markup=get_crops_list_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "cmd:regions")
async def cmd_regions_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Обрабатывает команду regions с клавиатуры."""
    await callback.message.edit_text(
        format_regions_list(),
        parse_mode="HTML",
        reply_markup=get_regions_list_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "cmd:help")
async def cmd_help_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Обрабатывает команду help с клавиатуры."""
    try:
        await callback.message.edit_text(
            format_help_message(),
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(),
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise
    await callback.answer()


@router.callback_query(F.data == "cmd:back_to_menu")
async def cmd_back_to_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Обрабатывает возврат в меню."""
    await state.clear()
    await callback.message.edit_text(
        format_start_message(),
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("zone:"), PredictionStates.waiting_for_zone)
async def select_zone(callback: CallbackQuery, state: FSMContext) -> None:
    """Обрабатывает выбор зоны."""
    zone_value = callback.data.replace("zone:", "")
    
    try:
        zone = AgriculturalZone(zone_value)
    except ValueError:
        await callback.answer("❌ Неизвестная зона")
        return
    
    await state.update_data(zone=zone_value)
    await state.set_state(PredictionStates.waiting_for_crop)
    await callback.message.edit_text(
        format_crop_selection(zone),
        parse_mode="HTML",
        reply_markup=get_crop_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "cmd:back_to_zones")
async def back_to_zones(callback: CallbackQuery, state: FSMContext) -> None:
    """Возвращает к выбору зоны."""
    await state.set_state(PredictionStates.waiting_for_zone)
    await callback.message.edit_text(
        format_zone_selection(),
        parse_mode="HTML",
        reply_markup=get_zone_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("crop:"), PredictionStates.waiting_for_crop)
async def select_crop(callback: CallbackQuery, state: FSMContext) -> None:
    """Обрабатывает выбор культуры."""
    crop_value = callback.data.replace("crop:", "")
    
    try:
        crop = CropType(crop_value)
    except ValueError:
        await callback.answer("❌ Неизвестная культура")
        return
    
    data = await state.get_data()
    zone = AgriculturalZone(data["zone"])
    
    await state.update_data(crop=crop_value)
    await state.set_state(PredictionStates.waiting_for_date)
    await callback.message.edit_text(
        format_sowing_date_prompt(zone, crop),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(PredictionStates.waiting_for_date)
async def input_sowing_date(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод даты посева и генерирует прогноз."""
    text = message.text.strip()
    
    # Разбор даты
    try:
        sowing_date = datetime.strptime(text, "%d.%m.%Y")
    except ValueError:
        await message.answer(
            "❌ <b>Ошибка:</b> Неверный формат даты. Используйте ДД.ММ.ГГГГ\n<i>Например: 15.04.2025</i>",
            parse_mode="HTML"
        )
        return
    
    # Проверка корректности даты
    if sowing_date.year < 2020 or sowing_date.year > 2030:
        await message.answer("❌ <b>Ошибка:</b> Год должен быть между 2020 и 2030", parse_mode="HTML")
        return
    
    # Получение данных из состояния
    data = await state.get_data()
    zone = AgriculturalZone(data["zone"])
    crop = CropType(data["crop"])
    
    # Генерация прогноза
    try:
        await message.answer("⏳ Генерирую прогноз...")
        
        forecast = forecast_season(
            zone=zone,
            crop=crop,
            sowing_date=sowing_date,
        )
        
        # Форматирование результата (графиков пока нет - пользователь может запросить их)
        result_text = format_forecast_result(forecast, show_menu=False)
        await message.answer(result_text, parse_mode="HTML")
        
        # Сохранение прогноза в БД (со всеми данными для восстановления графиков)
        try:
            user = get_or_create_user(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
            )
            
            # Расчёт общего риска
            all_risks = list(forecast.monthly_risk.values())
            if RiskLevel.RED in all_risks:
                overall_risk = RiskLevel.RED
            elif RiskLevel.YELLOW in all_risks:
                overall_risk = RiskLevel.YELLOW
            else:
                overall_risk = RiskLevel.GREEN
            
            # Преобразование стадий в сериализуемый формат (с погодными данными для каждой стадии)
            stages_data = []
            for stage in forecast.stages:
                stages_data.append({
                    "stage": stage.stage.value,
                    "start_date": stage.start_date.isoformat(),
                    "end_date": stage.end_date.isoformat(),
                    "disease_probability": stage.disease_forecast.probability,
                    "risk_level": stage.disease_forecast.risk_level.value,
                    "yield_contribution": stage.yield_contribution,
                    # Погодные данные для восстановления графиков
                    "temperature": stage.weather.temperature,
                    "humidity": stage.weather.humidity,
                    "precipitation": stage.weather.precipitation,
                })
            
            # Сохранение прогноза
            save_forecast(
                user=user,
                zone=zone,
                crop=crop,
                sowing_date=sowing_date,
                harvest_date=forecast.harvest_date,
                yield_forecast=forecast.yield_forecast,
                overall_risk=overall_risk,
                monthly_risk=forecast.monthly_risk,
                stages_data=stages_data,
            )
            
            await message.answer("✅ Прогноз сохранён в историю.", parse_mode="HTML")

            # Consume token if user is on token plan (monthly sub has priority)
            if not _is_monthly_active(message.from_user.id):
                result = consume_token(message.from_user.id)
                if result is not None:
                    remaining = get_token_count(message.from_user.id)
                    await message.answer(
                        TOKEN_CONSUMED.format(count=remaining),
                        parse_mode="HTML",
                    )
            
        except Exception as e:
            # Логируем, но не прерываем при ошибке сохранения в БД
            logger.error("Failed to save forecast for user {}: {}", message.from_user.id, e)
        
        # Сохранение данных прогноза в состоянии для генерации графиков
        await state.update_data(last_forecast={
            "zone": zone.value,
            "crop": crop.value,
            "sowing_date": sowing_date.isoformat(),
            "harvest_date": forecast.harvest_date.isoformat(),
            "yield_forecast": forecast.yield_forecast,
            "monthly_risk": forecast.monthly_risk,
            "stages": stages_data,
        })
        
        # Показ клавиатуры с опциями (не очищаем состояние - нужно для графиков)
        await message.answer(
            "Выберите действие:",
            reply_markup=get_new_forecast_keyboard(),
        )
        
    except Exception as e:
        await message.answer(f"❌ <b>Ошибка:</b> {str(e)}", parse_mode="HTML")
        await state.clear()


@router.callback_query(F.data == "new_forecast")
async def callback_new_forecast(callback: CallbackQuery, state: FSMContext) -> None:
    """Запускает новый прогноз с inline кнопки."""
    await state.clear()
    await state.set_state(PredictionStates.waiting_for_zone)
    await callback.message.edit_text(
        format_zone_selection(),
        parse_mode="HTML",
        reply_markup=get_zone_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "cmd:show_charts")
async def show_charts_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает графики для последнего прогноза - получает из базы данных."""
    # Попытка получить последний прогноз из базы данных
    try:
        user = get_or_create_user(telegram_id=callback.from_user.id)
        forecasts = list(get_user_forecasts(user, limit=1))
        
        if not forecasts:
            await callback.message.edit_text(
                "Нет сохранённых прогнозов. Создайте новый прогноз.",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard(),
            )
            await callback.answer()
            return
        
        forecast_record = forecasts[0]
        
        # Восстановление данных из базы данных
        zone = AgriculturalZone(forecast_record.zone)
        crop = CropType(forecast_record.crop)
        sowing_date = forecast_record.sowing_date
        harvest_date = forecast_record.harvest_date
        
        # Разбор стадий из JSON
        stages_data = json.loads(forecast_record.stages_json)
        monthly_risk = json.loads(forecast_record.monthly_risk_json)
        
        # Восстановление стадий
        stages = []
        for stage_data in stages_data:
            stage = StageInfo(
                stage=GrowingStage(stage_data["stage"]),
                start_date=datetime.fromisoformat(stage_data["start_date"]),
                end_date=datetime.fromisoformat(stage_data["end_date"]),
                weather=WeatherInput(
                    temperature=stage_data.get("temperature", 20.0),
                    humidity=stage_data.get("humidity", 60.0),
                    precipitation=stage_data.get("precipitation", 5.0),
                ),
                disease_forecast=DiseaseForecast(
                    probability=stage_data["disease_probability"],
                    risk_level=RiskLevel(stage_data["risk_level"]),
                    date=datetime.fromisoformat(stage_data["start_date"]),
                ),
                yield_contribution=stage_data.get("yield_contribution", 10.0),
            )
            stages.append(stage)
        
        # Создание SeasonForecast
        forecast = SeasonForecast(
            zone=zone,
            crop_type=crop,
            sowing_date=sowing_date,
            harvest_date=harvest_date,
            yield_forecast=forecast_record.yield_forecast,
            stages=stages,
            monthly_risk=monthly_risk,
        )
        
        # Отправка графиков через вспомогательную функцию
        await send_forecast_charts(callback, forecast, get_new_forecast_keyboard())
        
        await callback.answer()
        
    except Exception as e:
        logger.error("Error generating charts for user {}: {}", callback.from_user.id, e)
        await callback.message.answer(
            f"❌ Ошибка при генерации графиков: {str(e)}",
            parse_mode="HTML",
        )
        await callback.answer()


@router.callback_query(F.data.startswith("crop_info:"))
async def show_crop_info(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает подробную информацию о культуре."""
    crop_value = callback.data.replace("crop_info:", "")
    
    try:
        crop = CropType(crop_value)
    except ValueError:
        await callback.answer("❌ Неизвестная культура")
        return
    
    await callback.message.edit_text(
        format_crop_detail(crop),
        parse_mode="HTML",
        reply_markup=get_crops_list_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("region:"))
async def show_region_info(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает подробную информацию о регионе."""
    zone_value = callback.data.replace("region:", "")
    
    try:
        zone = AgriculturalZone(zone_value)
    except ValueError:
        await callback.answer("❌ Неизвестный регион")
        return
    
    await callback.message.edit_text(
        format_region_detail(zone),
        parse_mode="HTML",
        reply_markup=get_regions_list_keyboard(),
    )
    await callback.answer()


async def show_user_forecasts(
    message: Message,
    telegram_id: int,
    state: FSMContext,
    page: int = 0,
) -> None:
    """Показывает прогнозы пользователя."""
    try:
        user = get_or_create_user(telegram_id=telegram_id)
        forecasts = get_user_forecasts(user, limit=5, offset=page * 5)
        count = get_forecasts_count(user)
        
        if count == 0:
            await message.answer(
                format_no_forecasts(),
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard(),
            )
            return
        
        # Сохранение прогнозов в состоянии для пагинации
        await state.update_data(forecasts_page=page, forecasts_count=count)
        
        # Формирование сообщения
        msg = format_my_forecasts_header(count) + "\n\n"
        
        forecasts_list = list(forecasts)
        for i, f in enumerate(forecasts_list):
            idx = page * 5 + i + 1
            emoji = RISK_EMOJI.get(f.overall_risk, "⚪")
            msg += f"""<b>{idx}.</b> {f.zone_display} | {f.crop_display}
   📅 {f.sowing_date.strftime('%d.%m.%Y')} → {f.harvest_date.strftime('%d.%m.%Y')}
   {emoji} {f.yield_forecast:.1f} ц/га

 """
        
        # Добавление клавиатуры
        await message.answer(
            msg,
            parse_mode="HTML",
            reply_markup=get_myforecasts_keyboard(count, page),
        )
        
    except Exception as e:
        await message.answer(
            f"❌ Ошибка: {str(e)}",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(),
        )


@router.callback_query(F.data.startswith("forecast:view:"))
async def view_forecast(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает конкретный прогноз."""
    # Показывает первый прогноз (упрощённо)
    # В продакшене использовал бы callback data для получения конкретного прогноза
    try:
        user = get_or_create_user(telegram_id=callback.from_user.id)
        forecasts = list(get_user_forecasts(user, limit=1))
        
        if not forecasts:
            await callback.message.edit_text(
                format_no_forecasts(),
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard(),
            )
            await callback.answer()
            return
        
        forecast = forecasts[0]
        
        # Разбор полей JSON
        monthly_risk = json.loads(forecast.monthly_risk_json) if forecast.monthly_risk_json else {}
        
        await callback.message.edit_text(
            format_forecast_detail(forecast, monthly_risk),
            parse_mode="HTML",
            reply_markup=get_forecast_actions_keyboard(forecast.id),
        )
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")


@router.callback_query(F.data.startswith("forecast:charts:"))
async def show_forecast_charts(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает графики для сохранённого прогноза."""
    forecast_id = int(callback.data.split(":")[-1])
    
    try:
        forecast_record = get_forecast_by_id(forecast_id)
        if not forecast_record:
            await callback.answer("Прогноз не найден")
            return
        
        # Восстановление данных из базы данных
        zone = AgriculturalZone(forecast_record.zone)
        crop = CropType(forecast_record.crop)
        sowing_date = forecast_record.sowing_date
        harvest_date = forecast_record.harvest_date
        
        # Разбор стадий из JSON
        stages_data = json.loads(forecast_record.stages_json)
        monthly_risk = json.loads(forecast_record.monthly_risk_json)
        
        # Восстановление стадий
        stages = []
        for stage_data in stages_data:
            stage = StageInfo(
                stage=GrowingStage(stage_data["stage"]),
                start_date=datetime.fromisoformat(stage_data["start_date"]),
                end_date=datetime.fromisoformat(stage_data["end_date"]),
                weather=WeatherInput(
                    temperature=stage_data.get("temperature", 20.0),
                    humidity=stage_data.get("humidity", 60.0),
                    precipitation=stage_data.get("precipitation", 5.0),
                ),
                disease_forecast=DiseaseForecast(
                    probability=stage_data["disease_probability"],
                    risk_level=RiskLevel(stage_data["risk_level"]),
                    date=datetime.fromisoformat(stage_data["start_date"]),
                ),
                yield_contribution=stage_data.get("yield_contribution", 10.0),
            )
            stages.append(stage)
        
        # Создание SeasonForecast
        forecast = SeasonForecast(
            zone=zone,
            crop_type=crop,
            sowing_date=sowing_date,
            harvest_date=harvest_date,
            yield_forecast=forecast_record.yield_forecast,
            stages=stages,
            monthly_risk=monthly_risk,
        )
        
        # Отправка графиков через вспомогательную функцию
        await send_forecast_charts(callback, forecast, get_forecast_actions_keyboard(forecast_id))
        
        await callback.answer()
        
    except Exception as e:
        logger.error("Error generating charts for forecast {}: {}", forecast_id, e)
        await callback.message.answer(
            f"❌ Ошибка при генерации графиков: {str(e)}",
            parse_mode="HTML",
        )
        await callback.answer()


@router.callback_query(F.data.startswith("forecast:delete:"))
async def delete_forecast_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Удаляет прогноз."""
    forecast_id = int(callback.data.split(":")[-1])
    
    try:
        success = delete_forecast(forecast_id)
        if success:
            await callback.message.edit_text(
                "✅ Прогноз удалён.",
                parse_mode="HTML",
            )
        else:
            await callback.message.edit_text(
                "❌ Прогноз не найден.",
                parse_mode="HTML",
            )
            await callback.answer()
        
        # Обновление списка
        await show_user_forecasts(callback.message, callback.from_user.id, state)
        
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")


@router.callback_query(F.data.startswith("forecasts:page:"))
async def forecasts_pagination(callback: CallbackQuery, state: FSMContext) -> None:
    """Обрабатывает пагинацию списка прогнозов."""
    page = int(callback.data.split(":")[-1])
    await show_user_forecasts(callback.message, callback.from_user.id, state, page)
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def callback_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Обрабатывает кнопку отмены."""
    await state.clear()
    await callback.message.edit_text(
        format_cancel_message(),
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(),
    )
    await callback.answer()
