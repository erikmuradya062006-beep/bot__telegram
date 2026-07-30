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
    builder.button(text="📅 Book Appointment")
    builder.button(text="📋 My Appointments")
    builder.button(text="❌ Cancel Appointment")
    if is_admin:
        builder.button(text="🛠 Admin Panel")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def services_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for service in SERVICES:
        builder.button(text=service, callback_data=f"service:{service}")
    builder.button(text="« Back", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()


def doctors_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for doctor in DOCTORS:
        # Short name for the button
        short = doctor.split()[0] + " " + doctor.split()[1][0] + "."
        builder.button(text=short, callback_data=f"doctor:{doctor}")
    builder.button(text="« Back", callback_data="back_to_service")
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
        # Skip today if it's already late (after 4pm)
        if d == today and datetime.now().hour >= 16:
            continue
        text = d.strftime("%d.%m (%a)")
        # English day abbreviations
        weekdays_en = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        text = d.strftime("%d.%m") + f" ({weekdays_en[d.weekday()]})"
        builder.button(text=text, callback_data=f"date:{d.isoformat()}")
        count += 1
    builder.button(text="« Back", callback_data="back_to_doctor")
    builder.adjust(3)
    return builder.as_markup()


def times_kb(available_times: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for t in available_times:
        builder.button(text=t, callback_data=f"time:{t}")
    builder.button(text="« Back", callback_data="back_to_date")
    builder.adjust(3)
    return builder.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Confirm", callback_data="confirm_yes")
    builder.button(text="❌ Cancel", callback_data="confirm_no")
    builder.adjust(2)
    return builder.as_markup()


def cancel_appointments_kb(appointments: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ap in appointments:
        text = f"{ap['date']} {ap['time']} — {ap['service']}"
        builder.button(text=text, callback_data=f"cancel:{ap['id']}")
    builder.button(text="« Back", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()


def admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Today's Appointments", callback_data="admin_today")
    builder.button(text="📋 Upcoming Appointments", callback_data="admin_all")
    builder.button(text="« Close", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
