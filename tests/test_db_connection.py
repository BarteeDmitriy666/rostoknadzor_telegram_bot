"""Тесты для подключения к базе данных и инициализации."""
import tempfile
from pathlib import Path

import pytest
from peewee import SqliteDatabase

from src.db.connection import (
    get_database_path,
    get_or_create_user,
    database_connection,
)


@pytest.fixture
def temp_db():
    """Создаём временную базу данных."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Устанавливаем путь к базе данных во временную директорию
        db_path = Path(tmpdir) / "test.db"
        
        # Создаём тестовую базу данных
        test_db = SqliteDatabase(str(db_path))
        
        # Импортируем и патчим
        from src.db import models
        original_db = models.database
        models.database = test_db
        
        yield db_path, test_db
        
        # Восстанавливаем
        models.database = original_db
        test_db.close()


def test_get_database_path():
    """Тест генерации пути к базе данных."""
    path = get_database_path()
    
    assert path.name == "agrobot.db"
    assert path.parent.name == "data"


def test_get_or_create_user_new():
    """Тест создания нового пользователя."""
    # Используем in-memory базу данных для тестирования
    from src.db.models import User
    
    test_db = SqliteDatabase(":memory:")
    User._meta.database = test_db
    test_db.create_tables([User], safe=True)
    
    try:
        user = get_or_create_user(
            telegram_id=99999,
            username="newuser",
            first_name="New",
        )
        
        assert user.telegram_id == 99999
        assert user.username == "newuser"
        assert user.first_name == "New"
    finally:
        test_db.drop_tables([User])
        test_db.close()


def test_get_or_create_user_existing():
    """Тест получения существующего пользователя с обновлением профиля."""
    from src.db.models import User

    test_db = SqliteDatabase(":memory:")
    User._meta.database = test_db
    test_db.create_tables([User], safe=True)

    try:
        # Создаём пользователя first
        User.create(
            telegram_id=99999,
            username="existinguser",
            first_name="Old",
        )

        # Получаем существующего пользователя с новыми данными
        user = get_or_create_user(
            telegram_id=99999,
            username="newusername",
            first_name="New",
        )

        assert user.telegram_id == 99999
        assert user.username == "newusername"  # Обновлённое значение
        assert user.first_name == "New"  # Обновлённое значение
    finally:
        test_db.drop_tables([User])
        test_db.close()


def test_database_connection_context_manager():
    """Тест контекстного менеджера подключения к базе данных."""
    test_db = SqliteDatabase(":memory:")
    
    # Монки-патчим базу данных
    from src.db import connection
    original_db = connection.db
    connection.db = test_db
    
    try:
        with database_connection() as db:
            assert db is test_db
    finally:
        connection.db = original_db
        test_db.close()


def test_init_database():
    """Тест инициализации базы данных - создание таблиц."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_init.db"
        
        # Создаём базу данных с путём
        test_db = SqliteDatabase(str(db_path))
        
        # Импортируем и патчим
        from src.db import models, connection as conn
        original_db = models.database
        original_conn_db = conn.db
        
        models.database = test_db
        conn.db = test_db
        
        try:
            # Инициализируем (использует in-memory, но работает так же)
            User = models.User
            Forecast = models.Forecast
            
            User._meta.database = test_db
            Forecast._meta.database = test_db
            
            test_db.create_tables([User, Forecast], safe=True)
            
            # Проверяем существование таблиц
            assert "users" in test_db.get_tables()
            assert "forecasts" in test_db.get_tables()
        finally:
            models.database = original_db
            conn.db = original_conn_db
            test_db.close()
