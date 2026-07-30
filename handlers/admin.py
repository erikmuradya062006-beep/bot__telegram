from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from datetime import datetime, date

from config import ADMIN_IDS
from keyboards import admin_menu_kb, main_menu_kb
from database import get_all_active_appointments, get_appointments_by_date


def _format_date_short(value: str | date) -> str:
    if isinstance(value, str):
        return datetime.fromisoformat(value).strftime("%d.%m")
    return value.strftime("%d.%m")

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(F.text == "🛠 Admin Panel")
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("You do not have access.")
        return
    await message.answer(
        "🛠 <b>Admin Panel</b>\n\nChoose an action:",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_today")
async def admin_today(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    today = datetime.now().date().isoformat()
    appointments = await get_appointments_by_date(today)

    if not appointments:
        text = f"📅 No appointments for today ({datetime.now().strftime('%d.%m.%Y')})."
    else:
        text = f"📅 <b>Today's appointments ({datetime.now().strftime('%d.%m.%Y')}):</b>\n\n"
        for ap in appointments:
            text += (
                f"⏰ <b>{ap['time']}</b> — {ap['service']}\n"
                f"   Doctor: {ap['doctor']}\n"
                f"   Client: {ap['full_name']} ({ap['phone']})\n"
                f"   ID: #{ap['id']}\n\n"
            )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=admin_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "admin_all")
async def admin_all(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    appointments = await get_all_active_appointments(limit=30)

    if not appointments:
        text = "No upcoming active appointments."
    else:
        text = "📋 <b>Upcoming appointments:</b>\n\n"
        for ap in appointments:
            date_display = _format_date_short(ap["date"])
            text += (
                f"#{ap['id']} | {date_display} {ap['time']}\n"
                f"   {ap['service']} / {ap['doctor']}\n"
                f"   {ap['full_name']} — {ap['phone']}\n\n"
            )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=admin_menu_kb())
    await callback.answer()
