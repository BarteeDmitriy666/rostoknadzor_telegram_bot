"""Конфигурация с использованием Pydantic."""
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения."""

    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # YooMoney Payments
    yoomoney_receiver_wallet: str = Field(default="", alias="YOOMONEY_RECEIVER_WALLET")
    yoomoney_notification_secret: str = Field(default="", alias="YOOMONEY_NOTIFICATION_SECRET")
    yoomoney_access_token: str = Field(default="", alias="YOOMONEY_ACCESS_TOKEN")
    yoomoney_client_id: str = Field(default="", alias="YOOMONEY_CLIENT_ID")
    yoomoney_client_secret: str = Field(default="", alias="YOOMONEY_CLIENT_SECRET")
    yoomoney_redirect_uri: str = Field(
        default="https://yoomoney.ru/", alias="YOOMONEY_REDIRECT_URI"
    )

    # Subscription Settings
    token_price: float = Field(default=49.0, alias="TOKEN_PRICE")

    # Subscription tiers: duration_days -> price in RUB
    SUBSCRIPTION_TIERS: dict[int, int] = {
        30: 299,    # 1 месяц
        90: 549,    # 3 месяца
        180: 1199,  # 6 месяцев
    }

    @property
    def min_subscription_price(self) -> float:
        """Lowest tier price — used for admin display and fallback."""
        return float(min(self.SUBSCRIPTION_TIERS.values()))

    # Admin
    admin_ids: list[int] = Field(default=[], alias="ADMIN_IDS")

    # Webhook Server
    webhook_base_url: str = Field(default="", alias="WEBHOOK_BASE_URL")
    webhook_port: int = Field(default=8080, alias="WEBHOOK_PORT")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _parse_admin_ids(cls, v: Any) -> list[int]:
        """Разбирает ADMIN_IDS: одиночное число или строка через запятую."""
        if isinstance(v, list):
            return v
        if isinstance(v, int):
            return [v]
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                return []
            return [int(x.strip()) for x in stripped.split(",") if x.strip()]
        return []

    @field_validator("yoomoney_access_token", mode="before")
    @classmethod
    def _strip_access_token(cls, v: Any) -> str:
        """Strip whitespace from YOOMONEY_ACCESS_TOKEN."""
        if isinstance(v, str):
            return v.strip()
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()