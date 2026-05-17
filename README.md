# РОСТОКнадзор — ML-прогнозирование для сельского хозяйства

Telegram-бот для прогнозирования урожайности и риска заболеваний сельскохозяйственных культур на основе погодных данных и стадий роста.

## Быстрый старт

### 1. Настройка

**Linux / macOS:**

```bash
# Создать виртуальное окружение
python -m venv .venv

# Активировать
source .venv/bin/activate

# Установить зависимости
pip install -e ".[dev]"
```

**Windows:**

```cmd
:: Создать виртуальное окружение
python -m venv .venv

:: Активировать
.venv\Scripts\activate

:: Установить зависимости
pip install -e ".[dev]"
```

### 2. Создать файл .env

**Linux / macOS:**

```bash
cp .env.example .env
```

**Windows:**

```cmd
copy .env.example .env
```

Добавить в `.env`:

```
TELEGRAM_BOT_TOKEN=your_token_here
```

### 3. Обучение моделей

```bash
python -m src.ml.train
```

### 4. Запуск бота

```bash
python -m src.bot.main
```

## Команды

| Команда        | Описание                         |
| -------------- | -------------------------------- |
| `/start`       | Приветственное сообщение         |
| `/menu`        | Главное меню                     |
| `/predict`     | Начать прогнозирование           |
| `/myforecasts` | Просмотреть сохранённые прогнозы |
| `/crops`       | Информация о культурах           |
| `/regions`     | Информация о зонах               |
| `/help`        | Справка                          |
| `/cancel`      | Отменить текущее действие        |

## Python-команды

```bash
# Обучение моделей с кастомным количеством семплов
python -m src.ml.train -s 200 -o models

# Запуск бота
python -m src.bot.main

# Очистить базу данных
python -c "import os; os.remove('data/agrobot.db')"  # Linux/macOS
python -c "import os; os.remove('data/agrobot.db')"  # Windows

# Запуск тестов
pytest tests/ -v
```

## Обучение на собственном датасете

Модели можно обучить на реальных данных, передав путь к файлу через флаг `-r`.

### Формат данных

Поддерживаются форматы **CSV** и **Parquet**.

### Обязательные колонки

| Колонка               | Тип     | Описание                              |
| --------------------- | ------- | ------------------------------------- |
| `zone`                | string  | Сельскохозяйственная зона             |
| `crop_type`           | string  | Тип культуры                          |
| `growing_stage`       | string  | Стадия роста                          |
| `stage_day_of_year`   | int     | День года (1–366)                    |
| `temperature`         | float   | Температура, °C                       |
| `humidity`            | float   | Влажность, % (0–100)                  |
| `precipitation`       | float   | Осадки, мм (≥0)                       |
| `yield_value`         | float   | Урожайность, ц/га                     |
| `disease_probability` | float   | Вероятность заболевания (0–1)         |

### Допустимые значения

**Зоны (`zone`):**
`northwest`, `northeast`, `central_irrigated`, `azov`, `south`, `east`

**Культуры (`crop_type`):**
`winter_wheat`, `spring_barley`, `corn`, `oats`, `rye`, `millet`, `sorghum`, `peas`, `chickpeas`, `sunflower`, `sugar_beet`, `soybeans`, `flax`, `mustard`, `potatoes`, `tomatoes`, `onions`, `apples`, `plums`, `grapes`

**Стадии (`growing_stage`):**
`sowing`, `emergence`, `tillering`, `booting`, `heading_flowering`, `ripening_maturity`

### Пример CSV

```csv
zone,crop_type,growing_stage,stage_day_of_year,temperature,humidity,precipitation,yield_value,disease_probability
azov,winter_wheat,tillering,65,8.5,72,12.3,42.0,0.15
south,corn,emergence,120,18.2,55,5.0,38.5,0.08
central_irrigated,sunflower,heading_flowering,195,24.0,60,0.0,25.0,0.35
```

### Команда обучения с кастомным датасетом

```bash
# Обучение на реальных данных с аугментацией
python -m src.ml.train -r data/my_dataset.csv -a 5 -o models

# Параметры:
#   -r, --real-data       Путь к файлу с реальными данными (.csv или .parquet)
#   -a, --augment-factor  Сколько синтетических семплов сгенерировать
#                         на каждую группу реальных данных (по умолчанию 5)
#   -o, --output          Директория для сохранения моделей
#   --seed                Зерно случайности для воспроизводимости
```

При использовании реальных данных скрипт автоматически:
1. Загружает и валидирует данные (проверяет колонки, диапазоны значений)
2. Генерирует синтетические семплы на основе статистики реальных данных
3. Объединяет реальные и синтетические данные
4. Обучает модели урожайности и заболеваний

## Стек технологий

| Компонент    | Технология      |
| ------------ | --------------- |
| Telegram API | aiogram 3.x     |
| ML           | scikit-learn    |
| Графики      | matplotlib      |
| Данные       | pandas, numpy   |
| База данных  | peewee (SQLite) |
| Тесты        | pytest          |

## Доступные зоны

1. Northwest (Северо-Запад)
2. Northeast (Северо-Восток)
3. Central Irrigated (Центральный Орошаемый)
4. Azov (Азов)
5. South (Юг)
6. East (Восток)

## Доступные культуры

**Зерновые:** пшеница озимая, ячмень яровой, кукуруза, овёс, рожь, просо, сорго, горох, нут

**Технические:** подсолнечник, сахарная свёкла, соя, лён, горчица

**Овощи и фрукты:** картофель, томаты, лук, яблоки, сливы, виноград

## Важно

Модели обучены на реальных данных. Датасет - https://github.com/BarteeDmitriy666/rostoknadzor_telegram_bot/blob/main/dataset.csv
