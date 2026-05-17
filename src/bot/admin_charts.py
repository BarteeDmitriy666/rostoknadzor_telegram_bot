"""Генератор графиков для административной панели."""
from io import BytesIO

from matplotlib import pyplot as plt

from src.db import admin_repository


def _apply_common_style(fig: plt.Figure, ax: plt.Axes) -> None:
    """Применяет общий стиль к фигуре и осям."""
    fig.patch.set_facecolor("#f8f9fa")
    ax.set_facecolor("#ffffff")
    ax.grid(True, alpha=0.3, linestyle="--")


def generate_daily_usage_chart(days: int = 30) -> BytesIO:
    """Генерирует столбчатую диаграмму ежедневных прогнозов."""
    data = admin_repository.get_daily_forecast_stats(days)

    fig, ax = plt.subplots(figsize=(12, 5))
    _apply_common_style(fig, ax)

    if not data:
        ax.text(0.5, 0.5, "Нет данных", ha="center", va="center", fontsize=16)
        buf = _save_chart(fig)
        return buf

    dates = [str(row["date"]) for row in data]
    counts = [row["count"] for row in data]

    bars = ax.bar(dates, counts, color="#3498db", edgecolor="#333", linewidth=0.5)

    for bar, count in zip(bars, counts):
        ax.annotate(
            str(count),
            xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
            fontweight="bold",
        )

    ax.set_ylabel("Прогнозы", fontsize=11, fontweight="bold")
    ax.set_xlabel("Дата", fontsize=11, fontweight="bold")
    ax.set_title(f"Ежедневная активность ({days} дней)", fontsize=12, fontweight="bold", pad=15)

    plt.xticks(rotation=45, ha="right", fontsize=7)
    plt.tight_layout()

    return _save_chart(fig)


def generate_monthly_usage_chart(months: int = 12) -> BytesIO:
    """Генерирует линейный график помесячных прогнозов."""
    data = admin_repository.get_monthly_forecast_stats(months)

    fig, ax = plt.subplots(figsize=(10, 5))
    _apply_common_style(fig, ax)

    if not data:
        ax.text(0.5, 0.5, "Нет данных", ha="center", va="center", fontsize=16)
        buf = _save_chart(fig)
        return buf

    months_labels = [row["month"] for row in data]
    counts = [row["count"] for row in data]

    ax.plot(months_labels, counts, color="#27ae60", linewidth=2.5, marker="o", markersize=8)
    ax.fill_between(months_labels, counts, alpha=0.2, color="#27ae60")

    for i, count in enumerate(counts):
        ax.annotate(
            str(count),
            xy=(i, count),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=10,
            fontweight="bold",
        )

    ax.set_ylabel("Прогнозы", fontsize=11, fontweight="bold")
    ax.set_xlabel("Месяц", fontsize=11, fontweight="bold")
    ax.set_title("Помесячная активность", fontsize=12, fontweight="bold", pad=15)

    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    return _save_chart(fig)


def generate_subscription_chart() -> BytesIO:
    """Генерирует круговую диаграмму подписок (активные/неактивные)."""
    stats = admin_repository.get_subscription_stats()

    fig, ax = plt.subplots(figsize=(7, 7))
    fig.patch.set_facecolor("#f8f9fa")

    if stats["total"] == 0:
        ax.text(0.5, 0.5, "Нет подписок", ha="center", va="center", fontsize=16)
        buf = _save_chart(fig)
        return buf

    labels = ["Активные", "Неактивные"]
    sizes = [stats["active"], stats["inactive"]]
    colors = ["#27ae60", "#e74c3c"]
    explode = (0.05, 0)

    wedges, texts, autotexts = ax.pie(
        sizes,
        explode=explode,
        labels=labels,
        colors=colors,
        autopct="%1.1f%%",
        shadow=True,
        startangle=90,
        textprops={"fontsize": 12},
    )
    for autotext in autotexts:
        autotext.set_fontweight("bold")

    ax.set_title("Подписки", fontsize=14, fontweight="bold", pad=20)
    plt.tight_layout()

    return _save_chart(fig)


def generate_revenue_chart(days: int = 30) -> BytesIO:
    """Генерирует столбчатую диаграмму выручки по дням."""
    data = admin_repository.get_revenue_stats(days)

    fig, ax = plt.subplots(figsize=(12, 5))
    _apply_common_style(fig, ax)

    if not data:
        ax.text(0.5, 0.5, "Нет данных", ha="center", va="center", fontsize=16)
        buf = _save_chart(fig)
        return buf

    dates = [str(row["date"]) for row in data]
    totals = [row["total"] for row in data]

    bars = ax.bar(dates, totals, color="#f39c12", edgecolor="#333", linewidth=0.5)

    for bar, total in zip(bars, totals):
        if total > 0:
            ax.annotate(
                f"{total:.0f}₽",
                xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
                fontweight="bold",
            )

    ax.set_ylabel("Выручка (₽)", fontsize=11, fontweight="bold")
    ax.set_xlabel("Дата", fontsize=11, fontweight="bold")
    ax.set_title(f"Выручка за {days} дней", fontsize=12, fontweight="bold", pad=15)

    plt.xticks(rotation=45, ha="right", fontsize=7)
    plt.tight_layout()

    return _save_chart(fig)


def _save_chart(fig: plt.Figure) -> BytesIO:
    """Сохраняет фигуру в буфер и закрывает."""
    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=100, bbox_inches="tight", facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)
    return buf
