"""Модели базы данных для хранения прогнозов пользователей."""
import json
from datetime import datetime

from peewee import (
    AutoField,
    DateTimeField,
    FloatField,
    ForeignKeyField,
    IntegerField,
    Model,
    TextField,
)


# База данных будет установлена connection.py
database = None


class BaseModel(Model):
    """Базовая модель с общими полями."""

    id = AutoField()
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        database = database


class User(BaseModel):
    """Пользователь Telegram."""

    telegram_id = IntegerField(unique=True, index=True)
    username = TextField(null=True)
    first_name = TextField(null=True)
    last_name = TextField(null=True)
    language_code = TextField(default="ru")

    class Meta:
        table_name = "users"


class Forecast(BaseModel):
    """Запись прогноза пользователя."""

    user = ForeignKeyField(User, backref="forecasts", on_delete="CASCADE")
    zone = TextField()
    zone_display = TextField()
    crop = TextField()
    crop_display = TextField()
    sowing_date = DateTimeField()
    harvest_date = DateTimeField()
    yield_forecast = FloatField()
    overall_risk = TextField()
    monthly_risk_json = TextField()
    stages_json = TextField()

    # Метаданные модели
    model_version = TextField(default="1.0.0")

    class Meta:
        table_name = "forecasts"

    def get_monthly_risk(self) -> dict:
        """Возвращает месячный риск как словарь."""
        return json.loads(self.monthly_risk_json)

    def get_stages(self) -> list:
        """Возвращает стадии как список."""
        return json.loads(self.stages_json)


class Subscription(Model):
    """Подписка пользователя на прогнозы."""

    telegram_id = IntegerField(unique=True, primary_key=True)
    status = TextField(default="inactive")
    expires_at = DateTimeField(null=True)
    activated_at = DateTimeField(null=True)
    transaction_id = TextField(null=True)
    tokens = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        database = database
        table_name = "subscriptions"


class Payment(BaseModel):
    """Платёж пользователя через ЮMoney."""

    telegram_id = IntegerField(index=True)
    amount = FloatField()
    yoomoney_op_id = TextField(null=True)
    label = TextField()
    status = TextField(default="pending")
    payment_type = TextField(default="monthly")
    token_count = IntegerField(default=0)
    paid_at = DateTimeField(null=True)

    class Meta:
        table_name = "payments"
