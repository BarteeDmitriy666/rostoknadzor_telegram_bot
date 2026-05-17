"""Встроенные клавиатуры для меню бота."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from src.bot.localization import CROP_DISPLAY, STAGE_DISPLAY, ZONE_DISPLAY
from src.ml.dataset.schemas import CropType, GrowingStage


def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает постоянную reply клавиатуру с основными командами."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🌾 Новый прогноз"),
                KeyboardButton(text="📋 Мои прогнозы"),
            ],
            [
                KeyboardButton(text="🌻 О культурах"),
                KeyboardButton(text="🗺️ О регионах"),
            ],
            [
                KeyboardButton(text="❓ Помощь"),
                KeyboardButton(text="💳 Подписка"),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выберите действие...",
    )


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру главного меню со всеми командами."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌾 Новый прогноз", callback_data="cmd:predict"),
            InlineKeyboardButton(text="📋 Мои прогнозы", callback_data="cmd:myforecasts"),
        ],
        [
            InlineKeyboardButton(text="🌻 О культурах", callback_data="cmd:crops"),
            InlineKeyboardButton(text="🗺️ О регионах", callback_data="cmd:regions"),
        ],
        [
            InlineKeyboardButton(text="❓ Помощь", callback_data="cmd:help"),
            InlineKeyboardButton(text="💳 Подписка", callback_data="cmd:subscribe"),
        ],
    ])


def get_zone_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для выбора зоны."""
    buttons = [
        [InlineKeyboardButton(text=display, callback_data=f"zone:{zone.value}")]
        for zone, display in ZONE_DISPLAY.items()
    ]
    # Добавляем кнопку назад
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="cmd:back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_crop_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для выбора культуры."""
    crops = list(CropType)
    
    # Группируем по 2 в ряд
    buttons = []
    for i in range(0, len(crops), 2):
        row = []
        row.append(
            InlineKeyboardButton(
                text=CROP_DISPLAY.get(crops[i], crops[i].value),
                callback_data=f"crop:{crops[i].value}"
            )
        )
        if i + 1 < len(crops):
            row.append(
                InlineKeyboardButton(
                    text=CROP_DISPLAY.get(crops[i + 1], crops[i + 1].value),
                    callback_data=f"crop:{crops[i + 1].value}"
                )
            )
        buttons.append(row)
    
    # Добавляем кнопку назад
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="cmd:back_to_zones")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_regions_list_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для списка регионов."""
    buttons = [
        [InlineKeyboardButton(text=display, callback_data=f"region:{zone.value}")]
        for zone, display in ZONE_DISPLAY.items()
    ]
    # Добавляем кнопку возврата в меню
    buttons.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="cmd:back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_crops_list_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для списка культур."""
    crops = list(CropType)
    
    buttons = []
    for i in range(0, len(crops), 2):
        row = []
        row.append(
            InlineKeyboardButton(
                text=CROP_DISPLAY.get(crops[i], crops[i].value),
                callback_data=f"crop_info:{crops[i].value}"
            )
        )
        if i + 1 < len(crops):
            row.append(
                InlineKeyboardButton(
                    text=CROP_DISPLAY.get(crops[i + 1], crops[i + 1].value),
                    callback_data=f"crop_info:{crops[i + 1].value}"
                )
            )
        buttons.append(row)
    
    # Добавляем кнопку возврата в меню
    buttons.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="cmd:back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_forecast_actions_keyboard(forecast_id: int) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для действий с прогнозом (просмотр, графики, удаление)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Графики", callback_data=f"forecast:charts:{forecast_id}"),
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"forecast:delete:{forecast_id}"),
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="cmd:myforecasts"),
        ],
    ])


def get_myforecasts_keyboard(count: int, page: int = 0) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для списка моих прогнозов с пагинацией."""
    per_page = 5
    total_pages = (count + per_page - 1) // per_page
    
    buttons = []
    
    # Добавляем кнопки выбора прогноза (показываем последние 5)
    start_idx = page * per_page
    for i in range(start_idx, min(start_idx + per_page, count)):
        buttons.append([
            InlineKeyboardButton(text=f"📋 Прогноз #{i+1}", callback_data=f"forecast:view:{i}")
        ])
    
    # Элементы управления пагинацией
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"forecasts:page:{page-1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"forecasts:page:{page+1}"))
    
    if nav_row:
        buttons.append(nav_row)
    
    # Возврат в меню
    buttons.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="cmd:back_to_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_stage_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для выбора стадии роста."""
    buttons = [
        [InlineKeyboardButton(text=STAGE_DISPLAY.get(stage, stage.value), callback_data=f"stage:{stage.value}")]
        for stage in GrowingStage
    ]
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_yes_no_keyboard(action: str) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру да/нет."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"{action}:yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"{action}:no"),
        ]
    ])


def get_new_forecast_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру после генерации прогноза."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Показать графики", callback_data="cmd:show_charts"),
        ],
        [
            InlineKeyboardButton(text="🔄 Новый прогноз", callback_data="cmd:predict"),
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="cmd:back_to_menu"),
        ],
    ])


def get_subscription_inline_keyboard(
    payment_url: str, price: int
) -> InlineKeyboardMarkup:
    """Возвращает inline-клавиатуру с кнопкой оплаты подписки."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"💳 Оплатить {price}₽", url=payment_url
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔙 Главное меню", callback_data="cmd:back_to_menu"
            ),
        ],
    ])


def get_subscription_type_keyboard(
    tiers: dict[int, int], token_price: int
) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру выбора типа подписки с тарифами и токенами.

    tiers: {duration_days: price} e.g. {30: 299, 90: 549, 180: 1199}
    """
    from src.bot.localization import TIER_DISPLAY

    rows = []
    for days, price in sorted(tiers.items()):
        label = TIER_DISPLAY.get(days, f"{days // 30} мес.")
        rows.append([
            InlineKeyboardButton(
                text=f"📅 {label} — {price}₽",
                callback_data=f"sub:monthly:{days}",
            ),
        ])
    rows.append([
        InlineKeyboardButton(
            text=f"🪙 Купить токены — {token_price}₽/шт",
            callback_data="sub:tokens",
        ),
    ])
    rows.append([
        InlineKeyboardButton(
            text="🔙 Главное меню", callback_data="cmd:back_to_menu"
        ),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_token_count_keyboard(token_price: int) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру выбора количества токенов."""
    token_options = [1, 5, 10, 25]
    rows = []
    row = []
    for count in token_options:
        total = count * token_price
        row.append(
            InlineKeyboardButton(
                text=f"🪙 {count} — {total}₽",
                callback_data=f"sub:tokens:{count}",
            )
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="sub:type_select"),
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="cmd:back_to_menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Админ-панель ──────────────────────────────────────────


def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру главного меню админ-панели."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin:users:0"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats"),
        ],
        [
            InlineKeyboardButton(text="🔍 Найти по ID", callback_data="admin:find"),
        ],
        [
            InlineKeyboardButton(text="🔙 Главное меню", callback_data="cmd:back_to_menu"),
        ],
    ])


def get_admin_users_keyboard(
    users: list, page: int = 0, per_page: int = 10
) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру списка пользователей с пагинацией."""
    total = len(users)
    total_pages = max(1, (total + per_page - 1) // per_page)

    start_idx = page * per_page
    page_users = users[start_idx:start_idx + per_page]

    buttons = []
    for user in page_users:
        name = user.first_name or user.username or f"ID {user.telegram_id}"
        buttons.append([
            InlineKeyboardButton(
                text=f"👤 {name}",
                callback_data=f"admin:user:{user.telegram_id}",
            )
        ])

    # Пагинация
    nav_row = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin:users:{page - 1}")
        )
    if page < total_pages - 1:
        nav_row.append(
            InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"admin:users:{page + 1}")
        )
    if nav_row:
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton(text="🔙 Админ-меню", callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_user_actions_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру действий над пользователем."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Активировать 30д", callback_data=f"admin:sub:activate:{telegram_id}:30"
            ),
            InlineKeyboardButton(
                text="♾️ Навсегда", callback_data=f"admin:sub:activate:{telegram_id}:0"
            ),
        ],
        [
            InlineKeyboardButton(
                text="❌ Деактивировать", callback_data=f"admin:sub:deactivate:{telegram_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="➕ +7 дней", callback_data=f"admin:sub:extend:{telegram_id}:7"
            ),
            InlineKeyboardButton(
                text="➕ +30 дней", callback_data=f"admin:sub:extend:{telegram_id}:30"
            ),
        ],
        [
            InlineKeyboardButton(
                text="➖ -7 дней", callback_data=f"admin:sub:shrink:{telegram_id}:7"
            ),
            InlineKeyboardButton(
                text="➖ -30 дней", callback_data=f"admin:sub:shrink:{telegram_id}:30"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🪙 +5 токенов", callback_data=f"admin:tokens:add:{telegram_id}:5"
            ),
            InlineKeyboardButton(
                text="🪙 +10 токенов", callback_data=f"admin:tokens:add:{telegram_id}:10"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🪙 -5 токенов", callback_data=f"admin:tokens:remove:{telegram_id}:5"
            ),
            InlineKeyboardButton(
                text="🪙 -10 токенов", callback_data=f"admin:tokens:remove:{telegram_id}:10"
            ),
        ],
        [
            InlineKeyboardButton(text="👥 К списку", callback_data="admin:users:0"),
            InlineKeyboardButton(text="🔙 Админ-меню", callback_data="admin:menu"),
        ],
    ])


def get_admin_stats_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру меню статистики."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📈 Активность 30д", callback_data="admin:chart:daily"),
            InlineKeyboardButton(text="📈 Активность 12м", callback_data="admin:chart:monthly"),
        ],
        [
            InlineKeyboardButton(text="🥧 Подписки", callback_data="admin:chart:subs"),
            InlineKeyboardButton(text="💰 Выручка 30д", callback_data="admin:chart:revenue"),
        ],
        [
            InlineKeyboardButton(text="🔙 Админ-меню", callback_data="admin:menu"),
        ],
    ])
