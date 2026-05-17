"""Генератор графиков для визуализации прогнозов - русские подписи."""
from datetime import timedelta
from io import BytesIO

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.dates import DateFormatter, DayLocator, date2num
from matplotlib.patches import Rectangle

from src.bot.localization import CROP_DISPLAY, ZONE_DISPLAY
from src.ml.dataset.schemas import SeasonForecast


# Русские названия месяцев и подписи
MONTH_NAMES_RU = {
    1: "Янв", 2: "Фев", 3: "Мар", 4: "Апр",
    5: "Май", 6: "Июн", 7: "Июл", 8: "Авг",
    9: "Сен", 10: "Окт", 11: "Ноя", 12: "Дек",
}

STAGE_NAMES_RU = {
    "sowing": "Посев",
    "emergence": "Всходы",
    "tillering": "Кущение",
    "booting": "Выход в трубку",
    "heading_flowering": "Цветение",
    "ripening_maturity": "Созревание",
}


def generate_forecast_chart(forecast: SeasonForecast) -> BytesIO:
    """
    Генерирует график урожайности и риска заболеваний по времени.
    Версия с русскими подписями.
    
    Args:
        forecast: SeasonForecast с полной временной шкалой
    
    Returns:
        BytesIO буфер с изображением PNG
    """
    # Подготавливаем данные
    dates = []
    disease_probs = []
    yield_progress = []
    
    base_yield = forecast.yield_forecast
    
    for stage_info in forecast.stages:
        stage_start = stage_info.start_date
        stage_end = stage_info.end_date
        
        # Добавляем точки каждые 7 дней в пределах стадии
        current = stage_start
        while current <= stage_end:
            dates.append(current)
            disease_probs.append(stage_info.disease_forecast.probability)
            
            # Прогресс урожайности: накопительный по стадиям
            stage_progress = (current - stage_start).days / max(1, (stage_end - stage_start).days)
            prev_yield = sum(s.yield_contribution for s in forecast.stages[:forecast.stages.index(stage_info)])
            current_yield = prev_yield + stage_info.yield_contribution * stage_progress
            yield_progress.append(current_yield)
            
            current = current + timedelta(days=7)
    
    # Добавляем точку уборки
    dates.append(forecast.harvest_date)
    disease_probs.append(0.1)  # Низкий риск заболеваний при уборке
    yield_progress.append(base_yield)
    
    # Создаём фигуру с улучшенным стилем
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    # Устанавливаем стиль
    fig.patch.set_facecolor('#f8f9fa')
    ax1.set_facecolor('#ffffff')
    
    # Рисуем риск заболеваний
    color_disease = '#e74c3c'
    ax1.fill_between(dates, disease_probs, alpha=0.3, color=color_disease, label='Риск заболеваний')
    ax1.plot(dates, disease_probs, color=color_disease, linewidth=2, marker='o', markersize=4)
    ax1.set_xlabel('Дата', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Вероятность заболевания', color=color_disease, fontsize=11, fontweight='bold')
    ax1.tick_params(axis='y', labelcolor=color_disease)
    ax1.set_ylim(0, 1)
    
    # Рисуем урожайность
    ax2 = ax1.twinx()
    color_yield = '#27ae60'
    ax2.fill_between(dates, yield_progress, alpha=0.2, color=color_yield)
    ax2.plot(dates, yield_progress, color=color_yield, linewidth=2.5, marker='s', markersize=3, label='Урожайность')
    ax2.set_ylabel('Урожайность (ц/га)', color=color_yield, fontsize=11, fontweight='bold')
    ax2.tick_params(axis='y', labelcolor=color_yield)
    ax2.set_ylim(0, max(yield_progress) * 1.2)
    
    # Добавляем маркеры стадий
    for stage_info in forecast.stages:
        if stage_info.start_date >= dates[0] and stage_info.start_date <= dates[-1]:
            ax1.axvline(x=date2num(stage_info.start_date), color='#3498db', linestyle='--', alpha=0.5, linewidth=1)
    
    # Добавляем маркер уборки
    ax1.axvline(
        x=date2num(forecast.harvest_date),
        color='#9b59b6',
        linestyle='-',
        alpha=0.7,
        linewidth=2,
        label='Уборка урожая',
    )
    
    # Форматируем ось X
    ax1.xaxis.set_major_formatter(DateFormatter('%d.%m'))
    ax1.xaxis.set_major_locator(DayLocator(interval=14))
    plt.xticks(rotation=45, ha='right')
    
    # Заголовок с русским текстом через локализацию
    crop_display = CROP_DISPLAY.get(forecast.crop_type, forecast.crop_type.value)
    zone_display = ZONE_DISPLAY.get(forecast.zone, forecast.zone.value)
    title_text = (
        f"{crop_display} — {zone_display}\n"
        f"Посев: {forecast.sowing_date.strftime('%d.%m.%Y')} | "
        f"Уборка: {forecast.harvest_date.strftime('%d.%m.%Y')}"
    )
    plt.title(title_text, fontsize=12, fontweight='bold', pad=15)
    
    # Легенда
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', framealpha=0.9, fontsize=9)
    
    # Зоны уровня риска
    ax1.axhspan(0, 0.33, alpha=0.1, color='green')
    ax1.axhspan(0.33, 0.66, alpha=0.1, color='yellow')
    ax1.axhspan(0.66, 1.0, alpha=0.1, color='red')
    
    # Добавляем текст уровня риска на русском
    ax1.text(dates[-1], 0.16, 'НИЗКИЙ', fontsize=8, color='green', ha='right', alpha=0.7, fontweight='bold')
    ax1.text(dates[-1], 0.5, 'СРЕДНИЙ', fontsize=8, color='orange', ha='right', alpha=0.7, fontweight='bold')
    ax1.text(dates[-1], 0.83, 'ВЫСОКИЙ', fontsize=8, color='red', ha='right', alpha=0.7, fontweight='bold')
    
    # Сетка
    ax1.grid(True, alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    
    # Сохраняем в буфер
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)
    
    return buf


def generate_monthly_summary_chart(forecast: SeasonForecast) -> BytesIO:
    """
    Генерирует простую столбчатую диаграмму месячного риска с русскими подписями.
    
    Args:
        forecast: SeasonForecast с данными о месячном риске
    
    Returns:
        BytesIO буфер с изображением PNG
    """
    # Агрегируем по месяцам
    monthly_risk = {}
    for stage_info in forecast.stages:
        month_key = stage_info.start_date.strftime('%Y-%m')
        month_name = MONTH_NAMES_RU[stage_info.start_date.month]
        
        if month_key not in monthly_risk:
            monthly_risk[month_key] = {
                "name": month_name,
                "risks": [],
            }
        monthly_risk[month_key]["risks"].append(stage_info.disease_forecast.probability)
    
    # Усредняем риски по месяцам
    months = []
    avg_risks = []
    for key, data in sorted(monthly_risk.items()):
        months.append(data["name"])
        avg_risks.append(np.mean(data["risks"]))
    
    # Раскрашиваем столбцы по уровню риска
    colors = []
    for risk in avg_risks:
        if risk < 0.33:
            colors.append('#27ae60')  # Зелёный
        elif risk < 0.66:
            colors.append('#f39c12')  # Жёлтый
        else:
            colors.append('#e74c3c')  # Красный
    
    # Создаём фигуру с улучшенным стилем
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor('#f8f9fa')
    ax.set_facecolor('#ffffff')
    
    bars = ax.bar(months, avg_risks, color=colors, edgecolor='#333', linewidth=1)
    
    # Добавляем подписи значений
    for bar, risk in zip(bars, avg_risks):
        height = bar.get_height()
        ax.annotate(f'{risk:.0%}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # Добавляем легенду с русскими подписями
    legend_elements = [
        Rectangle((0,0),1,1, facecolor='#27ae60', label='Низкий (0-33%)'),
        Rectangle((0,0),1,1, facecolor='#f39c12', label='Средний (33-66%)'),
        Rectangle((0,0),1,1, facecolor='#e74c3c', label='Высокий (66-100%)'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=9)
    
    ax.set_ylabel('Риск заболевания', fontsize=11, fontweight='bold')
    ax.set_xlabel('Месяц', fontsize=11, fontweight='bold')
    ax.set_ylim(0, 1.1)
    ax.set_title('Ежемесячный риск заболеваний', fontsize=12, fontweight='bold', pad=15)
    
    # Добавляем горизонтальные линии-ориентиры
    ax.axhline(y=0.33, color='green', linestyle='--', alpha=0.3)
    ax.axhline(y=0.66, color='orange', linestyle='--', alpha=0.3)
    
    # Сетка
    ax.grid(True, alpha=0.3, axis='y', linestyle='--')
    
    plt.tight_layout()
    
    # Сохраняем в буфер
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)
    
    return buf
