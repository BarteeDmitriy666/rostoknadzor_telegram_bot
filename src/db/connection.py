"""Подключение к базе данных и инициализация."""
from contextlib import contextmanager
from pathlib import Path

from loguru import logger
from peewee import SqliteDatabase


def get_database_path() -> Path:
    """Возвращает путь к файлу базы данных."""
    db_dir = Path("data")
    db_dir.mkdir(exist_ok=True)
    return db_dir / "agrobot.db"


# Экземпляр базы данных
db = SqliteDatabase(
    str(get_database_path()),
    pragmas={
        "foreign_keys": 1,
        "journal_mode": "WAL",
        "busy_timeout": 5000,
    },
)


def init_database() -> None:
    """Инициализирует таблицы базы данных."""
    from src.db.models import User, Forecast, Payment, Subscription

    # Привязываем базу данных к моделям перед созданием таблиц
    User._meta.database = db
    Forecast._meta.database = db
    Subscription._meta.database = db
    Payment._meta.database = db

    db.create_tables([User, Forecast, Subscription, Payment], safe=True)
    logger.info("Database initialized: tables created")

    # Миграция: добавляем новые колонки, если их нет в существующих таблицах
    _migrate_add_column("subscriptions", "tokens", "INTEGER DEFAULT 0")
    _migrate_add_column("payments", "payment_type", "TEXT DEFAULT 'monthly'")
    _migrate_add_column("payments", "token_count", "INTEGER DEFAULT 0")


def _migrate_add_column(table: str, column: str, col_type: str) -> None:
    """Добавляет колонку в таблицу, если она ещё не существует."""
    cursor = db.execute_sql(f"PRAGMA table_info({table})")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if column not in existing_columns:
        db.execute_sql(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")


def close_database() -> None:
    """Закрывает подключение к базе данных."""
    db.close()
    logger.info("Database connection closed")


@contextmanager
def database_connection():
    """Контекстный менеджер для операций с базой данных (возвращает подключение)."""
    yield db


def get_or_create_user(
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> "User":
    """Получает или создаёт пользователя по Telegram ID.

    При существовании записи обновляет username, first_name, last_name
    актуальными данными из Telegram.
    """
    from src.db.models import User

    user, created = User.get_or_create(
        telegram_id=telegram_id,
        defaults={
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
        }
    )

    if created:
        logger.info("User created: id={} username={}", telegram_id, username)
    else:
        updates: dict = {}
        if username is not None and user.username != username:
            updates["username"] = username
        if first_name is not None and user.first_name != first_name:
            updates["first_name"] = first_name
        if last_name is not None and user.last_name != last_name:
            updates["last_name"] = last_name
        if updates:
            (User.update(**updates)
             .where(User.telegram_id == telegram_id)
             .execute())
            user = User.get_by_id(user.id)
            logger.debug("User updated: id={} fields={}", telegram_id, list(updates.keys()))

    return user
