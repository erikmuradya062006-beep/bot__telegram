from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from datetime import datetime, timedelta
from config import SERVICES, DOCTORS, MAX_DAYS_AHEAD, CLOSED_WEEKDAYS


def main_menu_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="📅 Записаться")
    builder.button(text="📋 Мои записи")
    builder.button(text="❌ Отменить запись")
    if is_admin:
        builder.button(text="🛠 Админ-панель")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def services_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for service in SERVICES:
        builder.button(text=service, callback_data=f"service:{service}")
    builder.button(text="« Назад", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()


def doctors_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for doctor in DOCTORS:
        # Короткое имя для кнопки
        short = doctor.split()[0] + " " + doctor.split()[1][0] + "."
        builder.button(text=short, callback_data=f"doctor:{doctor}")
    builder.button(text="« Назад", callback_data="back_to_service")
    builder.adjust(1)
    return builder.as_markup()


def dates_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    today = datetime.now().date()
    count = 0
    day = 0
    while count < MAX_DAYS_AHEAD:
        d = today + timedelta(days=day)
        day += 1
        if d.weekday() in CLOSED_WEEKDAYS:
            continue
        # Пропускаем сегодняшний день, если уже поздно (после 16:00)
        if d == today and datetime.now().hour >= 16:
            continue
        text = d.strftime("%d.%m (%a)")
        # Русские дни
        weekdays_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        text = d.strftime("%d.%m") + f" ({weekdays_ru[d.weekday()]})"
        builder.button(text=text, callback_data=f"date:{d.isoformat()}")
        count += 1
    builder.button(text="« Назад", callback_data="back_to_doctor")
    builder.adjust(3)
    return builder.as_markup()


def times_kb(available_times: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for t in available_times:
        builder.button(text=t, callback_data=f"time:{t}")
    builder.button(text="« Назад", callback_data="back_to_date")
    builder.adjust(3)
    return builder.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_yes")
    builder.button(text="❌ Отмена", callback_data="confirm_no")
    builder.adjust(2)
    return builder.as_markup()


def cancel_appointments_kb(appointments: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ap in appointments:
        text = f"{ap['date']} {ap['time']} — {ap['service']}"
        builder.button(text=text, callback_data=f"cancel:{ap['id']}")
    builder.button(text="« Назад", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()


def admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Записи на сегодня", callback_data="admin_today")
    builder.button(text="📋 Все ближайшие записи", callback_data="admin_all")
    builder.button(text="« Закрыть", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
